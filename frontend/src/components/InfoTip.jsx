export default function InfoTip({ text }) {
  return (
    <span className="info-tip" tabIndex={0}>
      <span className="info-tip-icon" aria-hidden="true">ℹ</span>
      <span className="info-tip-bubble" role="tooltip">{text}</span>
    </span>
  );
}
