"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = {
  href: string;
  label: string;
};

const clientNav: NavItem[] = [
  { href: "/", label: "Dashboard" },
  { href: "/monitoring", label: "Monitor" },
  { href: "/acompanhamentos", label: "Acompanhamentos" },
];

const adminNav: NavItem[] = [
  { href: "/admin/intelligence", label: "Intelligence" },
  { href: "/alerts", label: "Alertas globais" },
  { href: "/deliveries", label: "Entregas" },
  { href: "/notification-channels", label: "Canais" },
  { href: "/operations", label: "Operações" },
];

function isActive(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }

  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavLink({
  item,
  pathname,
}: {
  item: NavItem;
  pathname: string;
}) {
  const active = isActive(pathname, item.href);

  return (
    <Link
      href={item.href}
      className={[
        "block rounded-lg px-3 py-2 text-sm font-medium transition",
        active
          ? "bg-gray-900 text-white"
          : "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
      ].join(" ")}
    >
      {item.label}
    </Link>
  );
}

export default function AppShell({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-gray-100 lg:flex">
      <aside className="border-b border-gray-200 bg-white lg:fixed lg:inset-y-0 lg:left-0 lg:w-64 lg:border-b-0 lg:border-r">
        <div className="flex h-full flex-col">
          <div className="border-b border-gray-200 px-5 py-5">
            <Link href="/" className="block">
              <div className="text-lg font-bold text-gray-900">
                Newsroom AI
              </div>
              <div className="mt-1 text-xs text-gray-500">
                Institutional Intelligence
              </div>
            </Link>
          </div>

          <nav className="flex-1 space-y-6 px-3 py-4">
            <div>
              <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                Cliente
              </div>

              <div className="space-y-1">
                {clientNav.map((item) => (
                  <NavLink
                    key={item.href}
                    item={item}
                    pathname={pathname}
                  />
                ))}
              </div>
            </div>

            <div>
              <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                Admin
              </div>

              <div className="space-y-1">
                {adminNav.map((item) => (
                  <NavLink
                    key={item.href}
                    item={item}
                    pathname={pathname}
                  />
                ))}
              </div>
            </div>
          </nav>

          <div className="border-t border-gray-200 px-5 py-4 text-xs text-gray-400">
            MVP · ambiente de desenvolvimento
          </div>
        </div>
      </aside>

      <div className="min-w-0 flex-1 lg:pl-64">
        {children}
      </div>
    </div>
  );
}
