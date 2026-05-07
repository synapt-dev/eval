import type { Fixture } from "../types.ts";

export interface FixtureLoader {
  load(category: string): Promise<Fixture[]>;
  setup?(): Promise<void>;
  cleanup?(): Promise<void>;
}
