interface QualityBannerProps {
  message: string;
}

/**
 * Surfaces a per-series data-quality caveat inline, next to the chart it
 * applies to — the honest alternative to silently plotting a value the ETL
 * flagged as likely-imputed (see realgrowth.etl.derive.is_implausible_growth).
 */
export function QualityBanner({ message }: QualityBannerProps) {
  return (
    <div className="quality-banner" role="note">
      <span className="quality-banner__icon" aria-hidden="true">
        ⚠️
      </span>
      <span>{message}</span>
    </div>
  );
}
