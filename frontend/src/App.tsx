import { Navigate, Route, Routes } from 'react-router-dom';

import AppLayout from './components/AppLayout';
import RequireAuth from './auth/RequireAuth';
import AddFoodPage from './pages/AddFoodPage';
import DashboardPage from './pages/DashboardPage';
import HistoryPage from './pages/HistoryPage';
import LoginPage from './pages/LoginPage';
import NotFoundPage from './pages/NotFoundPage';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/add" element={<AddFoodPage />} />
        <Route path="/history" element={<HistoryPage />} />
      </Route>

      <Route path="/index.html" element={<Navigate to="/" replace />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
