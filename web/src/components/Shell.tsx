import { NavLink, Outlet, Link } from 'react-router-dom';

export default function Shell() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="h-14 border-b border-gray-200 bg-white flex items-center px-6 shrink-0">
        <Link to="/" className="text-lg font-medium tracking-tight text-gray-900 hover:text-accent transition-colors">
          Recourse
        </Link>
        
        <div className="flex-1" />
        
        <nav className="flex items-center gap-6 text-sm">
          <NavLink 
            to="/" 
            className={({isActive}) => 
              `transition-colors ${isActive ? 'text-accent font-semibold' : 'text-gray-600 hover:text-gray-900'}`
            }
          >
            Queue
          </NavLink>
          <NavLink 
            to="/metrics" 
            className={({isActive}) => 
              `transition-colors ${isActive ? 'text-accent font-semibold' : 'text-gray-600 hover:text-gray-900'}`
            }
          >
            Metrics
          </NavLink>
        </nav>
      </header>
      
      <main className="flex-1 bg-[#fafafa]">
        <Outlet />
      </main>
    </div>
  );
}
