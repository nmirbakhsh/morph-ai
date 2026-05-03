// Mirror of backend Pydantic schemas — keep in sync with backend/app/schemas.py.

export type Direction = "up" | "down" | "left" | "right";
export type Trend = "up" | "down" | "flat";
export type Theme =
  | "violet" | "emerald" | "coral" | "cerulean" | "amber"
  | "indigo" | "magenta" | "warm" | "neutral";

export interface StatItem {
  label: string;
  value: string;
  delta?: string | null;
  trend?: Trend | null;
}
export interface StatGrid {
  type: "stat_grid";
  items: StatItem[];
}
export interface ChartBlock {
  type: "chart";
  title: string;
  subtitle?: string | null;
  hero_value?: string | null;
  hero_delta?: string | null;
  series: number[];
}
export interface ListItemModel {
  title: string;
  subtitle?: string | null;
  value?: string | null;
  icon?: string | null;
}
export interface ListBlock {
  type: "list";
  title?: string | null;
  items: ListItemModel[];
}
export interface TextBlock {
  type: "text_block";
  title?: string | null;
  body: string;
}
export interface MetricBlock {
  type: "metric_block";
  label: string;
  value: string;
  sublabel?: string | null;
}
export interface TagRow {
  type: "tag_row";
  tags: string[];
}
export type Component =
  | StatGrid | ChartBlock | ListBlock | TextBlock | MetricBlock | TagRow;

export interface IntentSignpost {
  direction: Direction;
  label: string;
  sublabel: string;
  icon: string;
  intent_prompt: string;
  mcp_tool?: string | null;
  /** When set, navigation is a direct coord-shift to this existing node. */
  target_node_id?: string | null;
  is_back?: boolean;
  is_continuation?: boolean;
}
export interface AdjacentIntents {
  intents: IntentSignpost[];
}

export interface NodeLayout {
  theme: Theme;
  accent_color: string;
  bg_from?: string | null;
  bg_via?: string | null;
  bg_to?: string | null;
  bg_image_url?: string | null;
  icon: string;
  eyebrow: string;
  headline: string;
  headline_accent?: string | null;
  body?: string | null;
  components: Component[];
}

export interface NodeRecord {
  node_id: string;
  session_id: string;
  parent_node_id?: string | null;
  direction_from_parent?: Direction | null;
  coord_x: number;
  coord_y: number;
  mcp_tool_executed?: string | null;
  title: string;
  layout: NodeLayout;
  adjacent_intents: AdjacentIntents;
  created_at: string;
}

export interface Prefs {
  complexity: number; // 1..5
  density: number;    // 1..5
  contrast: number;   // 1..5
}

export interface InitResponse { session_id: string; node: NodeRecord; }
export interface NavigateResponse { node: NodeRecord; }
export interface ChatResponse {
  reply: string;
  teleport_node?: NodeRecord | null;
  followups: string[];
}
export interface GraphResponse { session_id: string; nodes: NodeRecord[]; }
