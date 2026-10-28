"""API integration tests — the full workflow end to end (tasks.md Phase 5)."""


class TestHealthAndBins:
    def test_health(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["service"] == "wastewise-api"

    def test_bins_list_has_seeded_data(self, client):
        r = client.get("/api/v1/bins")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 12
        assert body["items"][0]["id"] == "BIN-001"
        assert body["items"][0]["status"] in {"NORMAL", "WARNING", "CRITICAL"}

    def test_bins_filter_by_zone(self, client):
        r = client.get("/api/v1/bins", params={"zone": "North"})
        assert all(b["zone"] == "North" for b in r.json()["items"])

    def test_bin_detail_404(self, client):
        assert client.get("/api/v1/bins/BIN-999").status_code == 404
        assert client.get("/api/v1/bins/BIN-999").json()["error"]["code"] == "BIN_NOT_FOUND"

    def test_post_reading_computes_status_server_side(self, client):
        r = client.post(
            "/api/v1/bins/BIN-004/readings",
            json={"fill_percent": 95, "source": "simulator", "battery_percent": 80},
        )
        assert r.status_code == 201
        assert r.json()["fill_percent"] == 95
        # status visible in list
        statuses = {b["id"]: b["status"] for b in client.get("/api/v1/bins").json()["items"]}
        assert statuses["BIN-004"] == "CRITICAL"

    def test_post_reading_validation(self, client):
        r = client.post("/api/v1/bins/BIN-004/readings", json={"fill_percent": 150})
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_readings_history_newest_first(self, client):
        r = client.get("/api/v1/bins/BIN-001/readings", params={"limit": 5})
        items = r.json()["items"]
        assert len(items) == 5
        assert items[0]["measured_at"] >= items[-1]["measured_at"]


class TestDemoSimulation:
    def test_simulate_increases_fills(self, client):
        before = {b["id"]: b["fill_percent"] for b in client.get("/api/v1/bins").json()["items"]}
        r = client.post("/api/v1/demo/simulate", json={"steps": 2})
        assert r.status_code == 200
        assert r.json()["simulated"] is True
        after = {b["id"]: b["fill_percent"] for b in client.get("/api/v1/bins").json()["items"]}
        assert all(after[k] > before[k] for k in before)

    def test_demo_reset(self, client):
        client.post("/api/v1/demo/simulate", json={"steps": 1})
        r = client.post("/api/v1/demo/reset")
        assert r.status_code == 200
        assert r.json()["reset"] is True


class TestOptimizationWorkflow:
    def test_full_run(self, client):
        r = client.post(
            "/api/v1/optimization/runs",
            json={"depot_id": "DEPOT-001", "truck_id": "TRUCK-001",
                  "planning_horizon_hours": 12, "include_predicted_overflow": True},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["status"] in {"FEASIBLE", "PARTIAL"}
        assert body["solver"].startswith("OR-Tools") or "Heuristic" in body["solver"]

        # selected bins only from candidates (fill ≥ 75 or critical or predicted)
        for b in body["selected_bins"]:
            assert b["fill_percent"] >= 75 or b.get("predicted_fill_at_horizon", 0) >= 90

        # stops match selected + unserved
        stop_ids = [s["bin_id"] for s in body["stops"]]
        assert set(stop_ids) <= {b["bin_id"] for b in body["selected_bins"]}
        assert len(stop_ids) + len(body["unserved_bin_ids"]) == len(body["selected_bins"])

        # agents all recorded
        names = [a["agent_name"] for a in body["agents"]]
        for expected in ("load_snapshot", "bin_agent", "prediction_agent",
                         "route_agent", "fuel_agent", "recycling_agent"):
            assert expected in names

        # fuel math consistent with distance
        assert body["estimated_fuel_litres"] > 0
        assert body["estimated_fuel_cost"] > 0

        # persistence
        run_id = body["run_id"]
        detail = client.get(f"/api/v1/optimization/runs/{run_id}").json()
        assert detail["run_id"] == run_id
        assert detail["total_distance_km"] == body["total_distance_km"]

    def test_unknown_truck_404(self, client):
        r = client.post(
            "/api/v1/optimization/runs",
            json={"depot_id": "DEPOT-001", "truck_id": "TRUCK-999"},
        )
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "TRUCK_NOT_FOUND"

    def test_run_history(self, client):
        client.post("/api/v1/optimization/runs",
                    json={"depot_id": "DEPOT-001", "truck_id": "TRUCK-001"})
        r = client.get("/api/v1/optimization/runs")
        assert r.status_code == 200
        assert r.json()["total"] >= 1
        assert r.json()["items"][0]["agents"]  # agent briefs included


class TestForecasts:
    def test_forecast_ok(self, client):
        r = client.get("/api/v1/forecasts", params={"bin_id": "BIN-001", "horizon_hours": 12})
        assert r.status_code == 200
        body = r.json()
        assert body["bin_id"] == "BIN-001"
        assert body["method"] == "rolling-slope-v1"
        assert len(body["points"]) == 12
        assert body["points"][0]["target_at"].endswith("Z")

    def test_forecast_404(self, client):
        r = client.get("/api/v1/forecasts", params={"bin_id": "BIN-999"})
        assert r.status_code == 404


class TestRecycling:
    def test_classify_operator(self, client):
        r = client.post(
            "/api/v1/recycling/classifications",
            json={"bin_id": "BIN-001", "category": "plastic", "source": "operator"},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["category"] == "PLASTIC"  # normalized
        assert "recycler" in body["recommendation"].lower()
        assert body["review_status"] == "confirmed"

    def test_classify_invalid_category(self, client):
        r = client.post(
            "/api/v1/recycling/classifications",
            json={"category": "BANANA_SKIN"},
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "INVALID_CATEGORY"

    def test_hazardous_requires_review(self, client):
        r = client.post(
            "/api/v1/recycling/classifications",
            json={"bin_id": "BIN-006", "category": "HAZARDOUS", "source": "operator"},
        )
        assert r.status_code == 201
        assert r.json()["review_status"] == "review_required"

    def test_low_confidence_model_downgraded(self, client):
        r = client.post(
            "/api/v1/recycling/classifications",
            json={"bin_id": "BIN-008", "category": "METAL", "source": "model",
                  "confidence": 0.31},
        )
        assert r.status_code == 201
        body = r.json()
        assert body["category"] == "UNKNOWN"
        assert body["review_status"] == "review_required"

    def test_summary(self, client):
        r = client.get("/api/v1/recycling/summary")
        assert r.status_code == 200
        body = r.json()
        assert body["total_classifications"] >= 13
        assert body["review_required_count"] >= 1


class TestAlerts:
    def test_seeded_alerts_exist(self, client):
        r = client.get("/api/v1/alerts", params={"status": "OPEN"})
        assert r.status_code == 200
        types = {a["type"] for a in r.json()["items"]}
        assert "OVERFLOW_RISK" in types
        assert "SENSOR_STALE" in types
        assert "BATTERY_LOW" in types

    def test_acknowledge_then_resolve(self, client):
        alert = client.get("/api/v1/alerts", params={"status": "OPEN"}).json()["items"][0]
        r1 = client.post(f"/api/v1/alerts/{alert['id']}/acknowledge")
        assert r1.status_code == 200
        assert r1.json()["status"] == "ACKNOWLEDGED"
        r2 = client.post(f"/api/v1/alerts/{alert['id']}/resolve")
        assert r2.status_code == 200
        assert r2.json()["status"] == "RESOLVED"

    def test_invalid_transition_409(self, client):
        alert = client.get("/api/v1/alerts", params={"status": "OPEN"}).json()["items"][0]
        client.post(f"/api/v1/alerts/{alert['id']}/resolve")
        r = client.post(f"/api/v1/alerts/{alert['id']}/acknowledge")  # RESOLVED → ACK invalid
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "INVALID_TRANSITION"

    def test_alert_dedupe_on_reingest(self, client):
        before = client.get("/api/v1/alerts", params={"status": "OPEN", "severity": "CRITICAL"}).json()["total"]
        client.post("/api/v1/bins/BIN-001/readings", json={"fill_percent": 97})  # already critical
        after = client.get("/api/v1/alerts", params={"status": "OPEN", "severity": "CRITICAL"}).json()["total"]
        assert after == before  # no duplicate OPEN alert


class TestSettingsAndDashboard:
    def test_get_settings(self, client):
        r = client.get("/api/v1/settings")
        assert r.status_code == 200
        body = r.json()
        assert body["warning_threshold"] == 70.0
        assert body["critical_threshold"] == 90.0
        assert "fuel_price_per_litre" in body

    def test_patch_settings_validates(self, client):
        r = client.patch(
            "/api/v1/settings", json={"warning_threshold": 95, "critical_threshold": 90}
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "INVALID_THRESHOLDS"

    def test_patch_settings_applies(self, client):
        r = client.patch("/api/v1/settings", json={"fuel_price_per_litre": 99.0})
        assert r.status_code == 200
        assert r.json()["fuel_price_per_litre"] == 99.0

    def test_dashboard_summary(self, client):
        r = client.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        body = r.json()
        assert body["bins_total"] == 12
        assert body["bins_critical"] >= 3
        assert body["demo_mode"] is True
        assert len(body["zones"]) == 4

    def test_fleet_endpoints(self, client):
        assert len(client.get("/api/v1/fleet/trucks").json()) == 3
        assert client.get("/api/v1/fleet/depots").json()[0]["id"] == "DEPOT-001"

    def test_error_shape_is_consistent(self, client):
        r = client.get("/api/v1/bins/BIN-404")
        err = r.json()["error"]
        assert set(err) == {"code", "message", "request_id"}
        assert r.headers.get("X-Request-ID")
