import { NavLink } from 'react-router-dom'

export default function AdminTabs() {
  return (
    <nav className="admin-tabs">
      <NavLink
        to="/admin/users"
        className={({ isActive }) =>
          `admin-tab ${isActive ? 'admin-tab--active' : ''}`
        }
      >
        Users
      </NavLink>
      <NavLink
        to="/admin/departments"
        className={({ isActive }) =>
          `admin-tab ${isActive ? 'admin-tab--active' : ''}`
        }
      >
        Departments
      </NavLink>
      <NavLink
        to="/admin/clinics"
        className={({ isActive }) =>
          `admin-tab ${isActive ? 'admin-tab--active' : ''}`
        }
      >
        Clinics
      </NavLink>
      <NavLink
        to="/admin/institution"
        className={({ isActive }) =>
          `admin-tab ${isActive ? 'admin-tab--active' : ''}`
        }
      >
        Institution
      </NavLink>
    </nav>
  )
}
