import { NavLink, Outlet } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext';

/** Shell for all authenticated screens: header, nav, and logout. */
export default function AppLayout() {
  const { email, signOut } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header__inner">
          <div className="brand">
            <span className="brand__mark" aria-hidden="true">
              &#9679;
            </span>
            <span className="brand__name">Calorie Tracker</span>
          </div>

          <nav className="app-nav" aria-label="Main">
            <NavLink
              to="/"
              end
              className={({ isActive }) => `app-nav__link${isActive ? ' is-active' : ''}`}
            >
              Today
            </NavLink>
            <NavLink
              to="/add"
              className={({ isActive }) => `app-nav__link${isActive ? ' is-active' : ''}`}
            >
              Add Food
            </NavLink>
            <NavLink
              to="/history"
              className={({ isActive }) => `app-nav__link${isActive ? ' is-active' : ''}`}
            >
              History
            </NavLink>
          </nav>

          <div className="app-header__user">
            {email ? <span className="app-header__email">{email}</span> : null}
            <button type="button" className="btn btn--ghost" onClick={signOut}>
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
