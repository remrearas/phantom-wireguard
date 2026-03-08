export type UserRole = 'admin' | 'superadmin';

export interface NavItem {
  label: string;
  href?: string;
  roles: UserRole[];
  defaultExpanded?: boolean;
  children?: NavItem[];
}

export interface ProtectedNavContent {
  headerNav: NavItem[];
  sideNav: NavItem[];
}

export function filterByRole(items: NavItem[], role: UserRole): NavItem[] {
  return items
    .filter((item) => item.roles.includes(role))
    .map((item) => ({
      ...item,
      children: item.children ? filterByRole(item.children, role) : undefined,
    }));
}
