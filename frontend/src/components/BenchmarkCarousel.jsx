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

function SlideLayout({ line1, line2 }) {
  return (
    <>
      <p className="carousel-line1">{line1}</p>
      {line2 ? <p className="carousel-line2">{line2}</p> : <p className="carousel-line2">&nbsp;</p>}
    </>
  );
}

function SalaryAgeSlide({ cmp }) {
  const source = [cmp.salary_source, cmp.salary_source_metric].filter(Boolean).join(' · ');
  return (
    <SlideLayout
      line1={<>
        {cmp.user_age ? `Age ${cmp.user_age} · ` : ''}
        Median for {cmp.salary_band_label}: <strong>{gbp(cmp.median_monthly_salary)}/month</strong>
        {' · '}Your income of <strong>{gbp(cmp.current_monthly_salary)}/month</strong>{' '}
        is <strong>{pctDiff(cmp.salary_comparison_pct)}</strong> the typical figure
      </>}
      line2={source || null}
    />
  );
}

function RegionalSlide({ cmp }) {
  const notes = [cmp.region_source, cmp.is_london ? 'London: full-time employees only' : null].filter(Boolean).join(' · ');
  return (
    <SlideLayout
      line1={<>
        In <strong>{cmp.region}</strong>: median salary is{' '}
        <strong>{gbp(cmp.median_annual_salary_for_region)}/year</strong>
        {' · '}Your <strong>{gbp(cmp.current_annual_salary)}/year</strong>{' '}
        is <strong>{pctDiff(cmp.salary_vs_region_pct)}</strong> the regional median
      </>}
      line2={notes || null}
    />
  );
}

function PensionSlide({ cmp }) {
  if (!cmp.pension_data_available || !cmp.pension_band_label) {
    return (
      <SlideLayout
        line1={<em className="carousel-text-muted">Pension benchmark data not yet available for the {cmp.pension_band_label ?? 'your'} age group</em>}
        line2={null}
      />
    );
  }
  return (
    <SlideLayout
      line1={<>
        Median pension pot for age {cmp.pension_band_label}: <strong>{gbp(cmp.median_pension_pot)}</strong>
        {' · '}Your pot of <strong>{gbp(cmp.current_pension_pot)}</strong>{' '}
        is <strong>{pctDiff(cmp.pension_comparison_pct)}</strong> this
      </>}
      line2={cmp.pension_source || null}
    />
  );
}

function NoPensionSlide() {
  return (
    <SlideLayout
      line1={<>You haven&apos;t added a pension yet.{' '}
        <Link to="/pension" className="carousel-prompt-link">Add your pension pot</Link>{' '}
        to see how you compare.</>}
      line2="Pension comparison uses ONS Wealth and Assets Survey age-group benchmarks"
    />
  );
}

function NoIncomeSlide() {
  return (
    <SlideLayout
      line1={<>You haven&apos;t added an income source yet.{' '}
        <Link to="/income" className="carousel-prompt-link">Add your salary</Link>{' '}
        to see how you compare.</>}
      line2="Salary comparison uses ONS Annual Survey of Hours and Earnings (ASHE)"
    />
  );
}

function DobPromptSlide() {
  return (
    <SlideLayout
      line1={<>Add your date of birth to see how your salary and pension compare by age group —{' '}
        <Link to="/profile" className="carousel-prompt-link">Update profile</Link></>}
      line2={null}
    />
  );
}

function PostcodePromptSlide() {
  return (
    <SlideLayout
      line1={<>Add your postcode to see how your salary compares regionally —{' '}
        <Link to="/profile" className="carousel-prompt-link">Update profile</Link></>}
      line2={null}
    />
  );
}

function buildSlides(cmp, dobSet, postcodeSet, hasIncome) {
  const slides = [];

  if (dobSet) {
    if (cmp.salary_band_label) {
      if (hasIncome) {
        slides.push(<SalaryAgeSlide key="salary-age" cmp={cmp} />);
      } else {
        slides.push(<NoIncomeSlide key="no-income" />);
      }
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
    if ((cmp.current_pension_pot ?? 0) > 0) {
      slides.push(<PensionSlide key="pension" cmp={cmp} />);
    } else {
      slides.push(<NoPensionSlide key="no-pension" />);
    }
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
    <div
      className="card carousel-card"
      onTouchStart={onTouchStart}
      onTouchEnd={onTouchEnd}
    >
      <p className="carousel-heading">HOW YOU COMPARE</p>

      <div className="carousel-inner">
        {slides.length > 1 ? (
          <button className="carousel-arrow" onClick={prev} aria-label="Previous">‹</button>
        ) : (
          <span className="carousel-arrow-spacer" />
        )}

        <div className="carousel-content">
          {slides[clampedSlide]}
        </div>

        {slides.length > 1 ? (
          <button className="carousel-arrow" onClick={next} aria-label="Next">›</button>
        ) : (
          <span className="carousel-arrow-spacer" />
        )}
      </div>

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
  );
}
