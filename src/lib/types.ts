export interface ChainEvent {
  chain_id: string;
  category: string;
  event_name: string;
  raw_material: string;
  consumer_good: string;
  risk_assessment: {
    level: 1 | 2 | 3 | 4 | 5;
    badge_label: string;
    gpr_context: string;
  };
  timing_forecast: {
    lag_months: number;
    warning_message: string;
  };
  tangible_impact: {
    consumer_price_change_pct: number;
    real_world_example: string;
  };
  substitute_recommendations: Array<{
    item: string;
    reason: string;
  }>;
  storytelling: {
    headline: string;
    description: string;
  };
}

export type RiskLevel = ChainEvent["risk_assessment"]["level"];
