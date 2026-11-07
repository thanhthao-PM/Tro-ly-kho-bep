/**
 * TypeScript Data Contracts cho Module Assistant (Trợ lý AI Fact-based)
 * Ánh xạ 1:1 từ Pydantic assistant.py
 */

export interface ChatTurn {
  role: 'user' | 'assistant';
  text: string;
}

export interface AssistantMessageRequest {
  message: string;
  history?: ChatTurn[];
}

export interface VerifiedFact {
  id: string;
  tool: string;
  label: string;
  value: string;
  unit?: string;
  as_of: string;
}

export interface ProposedAction {
  type: 'OPEN_EXPIRING_BATCH' | 'OPEN_SHORTAGE' | 'OPEN_REPLENISHMENT' | 'OPEN_DISH';
  target_id?: string | null;
  label: string;
}

export interface RecommendationItem {
  text: string;
  assumptions: string[];
  basis: 'VERIFIED_FACT' | 'ESTIMATE';
}

export interface AssistantMessageResponse {
  answer_text: string;
  facts: VerifiedFact[];
  recommendations: RecommendationItem[];
  data_gaps: string[];
  proposed_actions: ProposedAction[];
  provider: 'rule_based' | 'external';
  request_id: string;
}
