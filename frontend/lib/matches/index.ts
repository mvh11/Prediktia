export { formatMatches } from "./formatMatches";
export { FormatMatchesError } from "./errors";
export type { FormatMatchesErrorCode } from "./errors";
export {
  categorizeFormattedMatch,
  partitionMatchesByBucket,
} from "./categorizeFormattedMatch";
export type { MatchBucket } from "./categorizeFormattedMatch";
export { API_URL, MATCHES_BASE_URL } from "@/lib/api";
export { fetchFormattedMatchesOnce } from "./fetchFormattedMatchesClient";
export type {
  ApiFootballFixtureItem,
  FormattedMatch,
  FormatMatchesOptions,
} from "./types";
