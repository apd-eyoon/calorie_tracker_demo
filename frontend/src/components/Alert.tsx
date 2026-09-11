interface Props {
  kind?: 'error' | 'success' | 'info';
  message: string;
  onDismiss?: () => void;
}

export default function Alert({ kind = 'error', message, onDismiss }: Props) {
  if (!message) return null;
  return (
    <div className={`alert alert--${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      <span>{message}</span>
      {onDismiss ? (
        <button type="button" className="alert__close" onClick={onDismiss} aria-label="Dismiss">
          &times;
        </button>
      ) : null}
    </div>
  );
}
