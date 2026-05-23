export type WeatherSnapshot = {
  precipitation_mm: number;
  temperature_c: number;
  is_raining: boolean;
};

export type VenueStatus = {
  venue_name: string;
  surface_type: string;
  wetness_level_pct: number;
  suitability_score: number;
  can_exercise: boolean;
  notice: string;
};

export type VenueWeatherStatusResponse = {
  location: string;
  weather_snapshot: WeatherSnapshot;
  venue_statuses: VenueStatus[];
};
