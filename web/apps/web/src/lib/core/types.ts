export interface Row {
  entry_id: unknown;
  label: string;
  options: string[];
}

export interface Question {
  label: string;
  type: string;
  type_code: number;
  entry_id: string;
  required: boolean;
  rows: Row[];
}

export interface Unit {
  index: number;
  question: string;
  label: string;
  options: string[];
  entry_id: unknown;
  required: boolean;
}

export interface FormSchema {
  title: string;
  description: string;
  questions: Question[];
  units: Unit[];
  reference_options: string[];
}

export interface AnalyzeError {
  error: string;
}

export type AnalyzeResult = FormSchema | AnalyzeError;

export type ConfigMode = "default" | "uniform" | "weighted";

export interface AnswerConfigData {
  mode: ConfigMode;
  weights: number[];
  overrides: Record<string, number[]>;
}

export type PickKind = "default" | "uniform" | "weighted";

export interface Resolved {
  kind: PickKind;
  weights: number[] | null;
}