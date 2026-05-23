import { apiRequest } from "@/lib/api/client";
import type { VenueWeatherStatusResponse } from "@/types/weather";

export function fetchVenueWeatherStatus() {
  return apiRequest<VenueWeatherStatusResponse>("/weather/venue-status");
}
