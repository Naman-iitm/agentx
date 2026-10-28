// Shared TypeScript types mirroring the backend API contracts.

export type FillStatus = "NORMAL" | "WARNING" | "CRITICAL";

export interface Bin {
  id: string;
  external_code: string;
  name: string;
  zone: string;
  latitude: number;
  longitude: number;
  bin_type: string;
  capacity_litres: number;
  is_active: boolean;
  fill_percent: number | null;
  status: FillStatus | null;
  battery_percent: number | null;
  measured_at: string | null;
  is_stale: boolean;
  reading_source: string | null;
}

export interface BinList { items: Bin[]; total: number; limit: number; offset: number; }

export interface Reading {
  id: number; bin_id: string; fill_percent: number; measured_at: string;
  source: string; battery_percent: number | null; quality_flag: string;
}
export interface ReadingList { items: Reading[]; total: number; limit: number; offset: number; }

export interface Truck {
  id: string; name: string; registration_label: string; capacity_litres: number;
  fuel_type: string; consumption_l_per_100km: number; is_active: boolean;
}

export interface Depot { id: string; name: string; latitude: number; longitude: number; is_active: boolean; }

export interface AgentResult {
  agent_name: string; status: "success" | "partial" | "skipped" | "failed";
  summary: string; reasons: string[]; warnings: string[]; duration_ms: number;
}

export interface SelectedBin {
  bin_id: string; name: string; zone: string; fill_percent: number; status: string;
  priority: number; demand_litres: number; predicted_fill_at_horizon: number | null;
  reasons: string[];
}

export interface RouteStop {
  sequence: number; bin_id: string; name: string; zone: string;
  distance_from_previous_km: number; demand_litres: number;
}

export interface Baseline { method: string; distance_km: number; fuel_litres: number; fuel_cost: number; }

export interface RecyclingRunSummary {
  distribution: Record<string, number>;
  recommendations: { category: string; recommendation: string; caution: string | null }[];
  diversion_estimate_percent: number | null;
  note: string;
}

export interface OptimizationRun {
  run_id: string; status: "FEASIBLE" | "PARTIAL" | "INFEASIBLE" | "FAILED" | "PENDING" | "RUNNING";
  solver: string; algorithm_version: string; requested_by: string | null;
  depot_id: string; truck_id: string; planning_horizon_hours: number;
  bins_evaluated: number; selected_bins: SelectedBin[]; stops: RouteStop[];
  unserved_bin_ids: string[]; total_distance_km: number; return_leg_km: number;
  estimated_fuel_litres: number; estimated_fuel_cost: number;
  baseline: Baseline | null; savings_percent: number | null;
  warnings: string[]; agents: AgentResult[]; recycling_summary: RecyclingRunSummary | null;
  started_at: string; completed_at: string | null; duration_ms: number;
}

export interface RunListItem {
  run_id: string; status: string; started_at: string; completed_at: string | null;
  total_distance_km: number; estimated_fuel_litres: number; estimated_fuel_cost: number;
  savings_percent: number | null; selected_count: number; solver: string;
  warnings: string[]; agents: { agent_name: string; status: string; duration_ms: number; warnings: string[] }[];
}
export interface RunList { items: RunListItem[]; total: number; limit: number; offset: number; }

export interface ForecastPoint {
  target_at: string; predicted_fill_percent: number; lower_bound: number; upper_bound: number;
}

export interface Forecast {
  bin_id: string; status: "ok" | "insufficient_history"; method: string; model_version: string;
  generated_at: string; horizon_hours: number; points: ForecastPoint[];
  warnings: string[]; note: string;
}

export interface Classification {
  id: number; bin_id: string | null; category: string; confidence: number | null;
  source: string; model_version: string | null; review_status: string;
  recommendation: string; caution: string | null; note: string | null; created_at: string;
}
export interface ClassificationList { items: Classification[]; total: number; limit: number; offset: number; }

export interface RecyclingSummary {
  total_classifications: number;
  distribution: { category: string; count: number; share_percent: number }[];
  recommendations: { category: string; recommendation: string; caution: string | null }[];
  review_required_count: number;
}

export interface Alert {
  id: number; bin_id: string | null; type: string; severity: string; status: string;
  title: string; message: string; created_at: string;
  acknowledged_at: string | null; resolved_at: string | null;
  acknowledged_by: string | null; resolved_by: string | null;
}
export interface AlertList { items: Alert[]; total: number; limit: number; offset: number; }

export interface Settings {
  warning_threshold: number; critical_threshold: number; collection_threshold: number;
  stale_after_hours: number; fuel_price_per_litre: number;
  default_consumption_l_per_100km: number; planning_horizon_hours: number;
  road_distance_factor: number; routing_provider: string; demo_mode: boolean; updated_at: string;
}

export interface DashboardSummary {
  bins_total: number; bins_critical: number; bins_warning: number; bins_normal: number;
  bins_stale: number; avg_fill_percent: number; open_alerts: number; critical_alerts: number;
  zones: { zone: string; bins: number; avg_fill_percent: number; critical_count: number }[];
  fleet_active: number;
  latest_run: { run_id: string; status: string; started_at: string; total_distance_km: number;
    estimated_fuel_cost: number; savings_percent: number | null; selected_count: number } | null;
  demo_mode: boolean;
}
