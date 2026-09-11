import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="page">
      <div className="empty-state">
        <h1 className="page__title">Page not found</h1>
        <p>The page you were looking for does not exist.</p>
        <Link className="btn btn--primary" to="/">
          Back to Today
        </Link>
      </div>
    </div>
  );
}
