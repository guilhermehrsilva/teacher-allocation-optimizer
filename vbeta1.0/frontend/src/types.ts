export type ValidationIssue = {
  severity: string;
  code: string;
  sheet: string;
  column: string;
  message: string;
  blocking: boolean;
  count: number;
  rows: number[];
};

export type ValidationReport = {
  source: string;
  status: "APROVADO" | "APROVADO_COM_RESSALVAS" | "REPROVADO";
  summary: {
    issue_groups: number;
    blocking_issue_groups: number;
    by_severity: Record<string, number>;
  };
  metadata: { allocating_rows: number; expected_module: number };
  issues: ValidationIssue[];
};

export type UploadResult = {
  id: string;
  filename: string;
  size_bytes: number;
  module: number;
  created_at: string;
  validation: ValidationReport;
};

export type Job = {
  id: string;
  upload_id: string;
  filename: string;
  module: number;
  status: string;
  message: string;
  validation_status: string;
  require_optimal: boolean;
  time_limit_seconds: number | null;
  kind: "PRIMARY" | "SCENARIO";
  scenario_id: string | null;
  is_official: boolean;
  round: string | null;
  exit_code: number | null;
  created_at: string;
  updated_at: string;
  history: Array<{ state: string; message: string; at_utc: string }>;
  terminal: boolean;
};

export type ScenarioChange = {
  id: string;
  change_type: "CAPACIDADE" | "AGENDA" | "COMPATIBILIDADE";
  entity_type: "teacher" | "offer";
  row_number: number;
  field_name: string;
  old_value: string | number | null;
  new_value: string | number;
  created_at: string;
};

export type ScenarioPolicy = {
  id: string;
  policy_type: "ALOCAR_CLUSTER" | "INTERNALIZACAO" | "PRIORIDADE" | "FIXAR";
  target_type: "GLOBAL" | "CLUSTER" | "COURSE" | "OFFER";
  target_value: string;
  configuration: Record<string, string | number | boolean>;
  created_at: string;
};

export type Scenario = {
  id: string;
  baseline_job_id: string;
  baseline_round: string | null;
  baseline_filename: string;
  module: number;
  name: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
  promoted_at: string | null;
  official_job_id: string | null;
  changes: ScenarioChange[];
  policies: ScenarioPolicy[];
  latest_job: Job | null;
};

export type ScenarioCatalog = {
  teachers: Array<{
    row_number: number;
    badge: string;
    name: string;
    status: string;
    job_function: string;
    teaching_capacity: number;
    profile: string;
  }>;
  offers: Array<{
    row_number: number;
    course: string;
    course_code: string;
    course_name: string;
    discipline_code: string;
    discipline_name: string;
    day: string;
    time: string;
    order: string;
    cluster: string;
    profile: string;
    baseline_status: string;
    baseline_teacher_badge: string;
    baseline_teacher_name: string;
  }>;
  courses: Array<{ code: string; name: string }>;
  clusters: Array<{ name: string; total_offers: number; unassigned_offers: number }>;
};

export type ScenarioDifference = {
  source_row: number;
  discipline_code: string;
  discipline_name: string;
  before_teacher: string | null;
  after_teacher: string | null;
};

export type ScenarioComparison = {
  scenario: Scenario;
  baseline_job: Job;
  scenario_job: Job;
  kpis: {
    baseline_coverage_pct: number;
    scenario_coverage_pct: number;
    coverage_delta_pp: number;
    allocated_delta: number;
    unassigned_hours_delta: number;
    used_teachers_delta: number;
    internal_allocated_hours_delta: number;
    external_allocated_hours_delta: number;
    assignment_stability_pct: number;
    first_stage_hours_delta: number;
    second_stage_hours_delta: number;
  };
  differences: {
    recovered: ScenarioDifference[];
    lost: ScenarioDifference[];
    reassigned: ScenarioDifference[];
  };
  guardrails: {
    validation: string;
    solver: string;
    audit: string;
    eligible_for_promotion: boolean;
  };
};

export type Summary = {
  status: string;
  solver_status: string;
  transmissions: number;
  allocated: number;
  unassigned: number;
  active_teachers: number;
  used_teachers: number;
  zero_active_teachers: number;
  wall_time_seconds: number;
  unassigned_reasons: Record<string, number>;
};

export type Allocation = {
  transmission_id: number;
  source_row: number;
  curriculum: string;
  discipline_code: string;
  discipline_name: string;
  status: string;
  unassigned_reason: string;
  allocation_reason: string;
  eligible_teacher_count: number;
  contract_model: string;
  teacher_badge: string | null;
  teacher_name: string | null;
};

export type AllocationPage = {
  items: Allocation[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
};

export type DashboardData = {
  job: Job;
  kpis: {
    coverage_pct: number;
    allocated: number;
    transmissions: number;
    unassigned: number;
    teacher_use_pct: number;
    active_teachers: number;
    used_teachers: number;
    zero_active_teachers: number;
    disciplines_by_order: { first: number; second: number; extended: number };
    first_stage_demand_hours: number;
    second_stage_demand_hours: number;
    first_stage_capacity_delta_hours: number;
    second_stage_capacity_delta_hours: number;
    active_teaching_capacity_hours: number;
  };
  unassigned_reasons: Array<{ reason: string; count: number }>;
  stage_hours: { first_stage?: number; second_stage?: number };
  charts: {
    by_day: Array<{ day: string; disciplines: number; teachers: number }>;
    demand_hours_by_cluster: Array<{ cluster: string; hours: number }>;
  };
  filters: {
    selected: Record<string, string[]>;
    options: {
      orders: string[];
      courses: Array<{ value: string; label: string }>;
      clusters: string[];
      days: string[];
      times: string[];
    };
  };
  guardrails: { validation: string; solver: string; audit: string };
  wall_time_seconds: number;
  metric_notes: { demand: string; capacity_delta: string };
  source_note: string;
};

export type DashboardFilters = {
  order: string[];
  course: string[];
  cluster: string[];
  day: string[];
  time: string[];
};

export type InsightBreakdown = {
  label: string;
  count: number;
  share_pct: number;
};

export type InsightsData = {
  job: Job;
  kpis: {
    coverage_pct: number;
    courses_below_90_pct: number;
    disciplines_uncovered: number;
    unassigned_demand_hours: number;
    rpa_allocated_hours: number;
    internal_idle_hours: number;
    top_20_teacher_share_pct: number;
    median_peak_utilization_pct: number;
    high_or_critical_risk_teachers: number;
    load_outliers: number;
    single_candidate_allocations: number;
    pareto_teacher_count_80: number;
  };
  stage_load: {
    first_stage_allocations: number;
    second_stage_allocations: number;
    difference: number;
  };
  teacher_stats: {
    used_teachers: number;
    mean_allocations: number;
    median_allocations: number;
    pareto_count_80: number;
    top_20_count: number;
    top_20_share_pct: number;
  };
  teacher_distribution: Array<{
    teacher: string;
    role: string;
    allocations: number;
    share_pct: number;
    cumulative_pct: number;
    stage_1_utilization_pct: number;
    stage_2_utilization_pct: number;
  }>;
  risk_teachers: Array<{
    teacher: string;
    role: string;
    allocations: number;
    stage_1_utilization_pct: number;
    stage_2_utilization_pct: number;
    peak_utilization_pct: number;
    day_concentration_pct: number;
    score: number;
    risk_class: string;
    load_outlier: boolean;
  }>;
  breakdowns: {
    clusters: InsightBreakdown[];
    days: InsightBreakdown[];
    coordinators: InsightBreakdown[];
    contracts: InsightBreakdown[];
    unassigned_reasons: InsightBreakdown[];
  };
  automatic_insights: Array<{
    tone: "neutral" | "attention" | "critical" | "positive";
    title: string;
    text: string;
  }>;
  coverage: {
    courses: Array<{
      curso: string;
      nome_curso: string;
      total: number;
      allocated: number;
      unassigned: number;
      coverage_pct: number;
      demand_hours: number;
      single_candidate: number;
      gap_days: Array<{ day: string; count: number }>;
    }>;
    clusters: Array<{
      cluster: string;
      total: number;
      allocated: number;
      unassigned: number;
      coverage_pct: number;
      demand_hours: number;
      single_candidate: number;
      gap_days: Array<{ day: string; count: number }>;
    }>;
    discipline_gaps: Array<{
      curso: string;
      nome_curso: string;
      cod_disciplina: string;
      nome_disciplina: string;
      total: number;
      allocated: number;
      unassigned: number;
      coverage_pct: number;
      demand_hours: number;
      single_candidate: number;
    }>;
    gap_reasons: InsightBreakdown[];
  };
  opportunities: Array<{
    priority: string;
    kind: string;
    title: string;
    metric: string;
    impact: string;
    action: string;
  }>;
  diagnostics: {
    most_congested_unassigned_slots: Array<{
      slot: string;
      count: number;
      affected_courses: number;
      top_course: string;
      top_course_count: number;
      top_profile: string;
    }>;
    top_gap_profile: string | null;
  };
  methodology: string[];
  limitations: string[];
  source_note: string;
};
