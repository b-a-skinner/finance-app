import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { gbp } from '../utils/format';

function pctDiff(pct) {
  if (pct === null || pct === undefined) return null;
  const abs = Math.abs(pct - 100).toFixed(1);
  if (pct > 101) return `${abs}% above`;
  if (pct < 99)  return `${abs}% below`;
  return 'in line with';
}

function SalaryAgeSlide({ cmp }) {
  return (
    <div className="carousel-slide">
      <p className="carousel-slide-text">
        {cmp.user_age != null ? `You're ${cmp.user_age}. ` : ''}
        People aged {cmp.salary_band_label} earn a median of <strong>{gbp(cmp.median_monthly_salary)}/month</strong>.
        {' '}Your monthly income of <strong>{gbp(cmp.current_monthly_salary)}</strong> is{' '}
        <strong>{pctDiff(cmp.salary_comparison_pct)}</strong> the typical figure for your age group.
      </p>
      {cmp.salary_source && (
        <p className="benchmark-source">{cmp.salary_source} · {cmp.salary_source_metric}</p>
      )}
    </div>
  );
}

function RegionalSlide({ cmp }) {
  return (
    <div className="carousel-slide">
      <p className="carousel-slide-text">
        In <strong>{cmp.region}</strong>, the typical salary is{' '}
        <strong>{gbp(cmp.median_annual_salary_for_region)}/year</strong>.
        {' '}Your annual income of <strong>{gbp(cmp.current_annual_salary)}</strong> is{' '}
        <strong>{pctDiff(cmp.salary_vs_region_pct)}</strong> the regional median.
      </p>
      {cmp.region_source && (
        <p className="benchmark-source">{cmp.region_source}</p>
      )}
      {cmp.is_london && (
        <p className="benchmark-source benchmark-caveat">
          London figure is full-time employees only and may overstate the typical comparison.
        </p>
      )}
    </div>
  );
}

function PensionSlide({ cmp }) {
  if (!cmp.pension_data_available || !cmp.pension_band_label) {
    return (
      <div className="carousel-slide">
        <p className="carousel-slide-text benchmark-unavailable">
          Benchmark data not yet available for the {cmp.pension_band_label ?? 'your'} age group.
        </p>
      </div>
    );
  }
  return (
    <div className="carousel-slide">
      <p className="carousel-slide-text">
        People aged {cmp.pension_band_label} have a median pension pot of{' '}
        <strong>{gbp(cmp.median_pension_pot)}</strong>.
        {' '}Your current pot of <strong>{gbp(cmp.current_pension_pot)}</strong> is{' '}
        <strong>{pctDiff(cmp.pension_comparison_pct)}</strong> this.
      </p>
      {cmp.pension_source && (
        <p className="benchmark-source">{cmp.pension_source}</p>
      )}
    </div>
  );
}

function DobPromptSlide() {
  return (
    <div className="carousel-slide">
      <p className="carousel-slide-text">
        Add your date of birth to see how your salary and pension compare by age group.
      </p>
      <Link to="/profile" className="carousel-prompt-link">Update profile →</Link>
    </div>
  );
}

function PostcodePromptSlide() {
  return (
    <div className="carousel-slide">
      <p className="carousel-slide-text">
        Add your postcode to see how your salary compares regionally.
      </p>
      <Link to="/profile" className="carousel-prompt-link">Update profile →</Link>
    </div>
  );
}

function buildSlides(cmp, dobSet, postcodeSet, hasIncome) {
  const slides = [];

  if (dobSet) {
    if (cmp.salary_band_label && hasIncome) {
      slides.push(<SalaryAgeSlide key="salary-age" cmp={cmp} />);
    }
  } else {
    slides.push(<DobPromptSlide key="dob-prompt" />);
  }

  if (postcodeSet) {
    if (cmp.region && cmp.median_annual_salary_for_region != null && hasIncome) {
      slides.push(<RegionalSlide key="regional" cmp={cmp} />);
    }
  } else {
    slides.push(<PostcodePromptSlide key="postcode-prompt" />);
  }

  if (dobSet && cmp.pension_band_label) {
    slides.push(<PensionSlide key="pension" cmp={cmp} />);
  }

  return slides;
}

export default function BenchmarkCarousel({ comparison, profile }) {
  const [slide, setSlide] = useState(0);
  const touchStartX = useRef(null);

  if (!comparison) return null;

  const dobSet      = !!profile?.date_of_birth;
  const postcodeSet = !!profile?.postcode_outward;
  const hasIncome   = (comparison.current_monthly_salary ?? 0) > 0;

  const slides = buildSlides(comparison, dobSet, postcodeSet, hasIncome);
  if (slides.length === 0) return null;

  const clampedSlide = Math.min(slide, slides.length - 1);

  function prev() { setSlide(i => (i - 1 + slides.length) % slides.length); }
  function next() { setSlide(i => (i + 1) % slides.length); }

  function onTouchStart(e) { touchStartX.current = e.touches[0].clientX; }
  function onTouchEnd(e) {
    if (touchStartX.current === null) return;
    const diff = touchStartX.current - e.changedTouches[0].clientX;
    if (Math.abs(diff) > 50) diff > 0 ? next() : prev();
    touchStartX.current = null;
  }

  return (
    <div className="carousel-section">
      <p className="carousel-heading">HOW YOU COMPARE</p>
      <div
        className="card carousel-card"
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
      >
        {slides.length > 1 && (
          <button className="carousel-arrow carousel-arrow--left" onClick={prev} aria-label="Previous">‹</button>
        )}

        <div className="carousel-body">
          {slides[clampedSlide]}
        </div>

        {slides.length > 1 && (
          <button className="carousel-arrow carousel-arrow--right" onClick={next} aria-label="Next">›</button>
        )}

        {slides.length > 1 && (
          <div className="carousel-dots">
            {slides.map((_, i) => (
              <button
                key={i}
                className={`carousel-dot${i === clampedSlide ? ' carousel-dot--active' : ''}`}
                onClick={() => setSlide(i)}
                aria-label={`Slide ${i + 1}`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
