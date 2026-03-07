import React, { useState, useEffect, useCallback } from 'react';
import {
  Grid,
  Column,
  DataTable,
  Table,
  TableHead,
  TableRow,
  TableHeader,
  TableBody,
  TableCell,
  TableContainer,
  TableToolbar,
  TableToolbarContent,
  Button,
  Tag,
  OverflowMenu,
  OverflowMenuItem,
  PasswordInput,
  TextInput,
  InlineNotification,
  Stack,
} from '@carbon/react';
import { Add, Renew, Checkmark, Close } from '@carbon/icons-react';
import { useUser } from '@shared/contexts/UserContext';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import { apiClient } from '@shared/api/client';
import { Navigate } from 'react-router-dom';
import './styles/user-management.scss';

const PASSWORD_PATTERN = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{}|;:'",.<>?/`~\\]).{8,256}$/;
const PASSWORD_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*_+-=';

function generatePassword(length = 16): string {
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  let pw = '';
  for (const byte of array) pw += PASSWORD_CHARS[byte % PASSWORD_CHARS.length];
  if (!/[a-z]/.test(pw)) pw = pw.slice(0, -1) + 'a';
  if (!/[A-Z]/.test(pw)) pw = pw.slice(0, -1) + 'A';
  if (!/\d/.test(pw)) pw = pw.slice(0, -1) + '1';
  if (!/[!@#$%^&*_+\-=]/.test(pw)) pw = pw.slice(0, -1) + '!';
  return pw;
}

interface UserInfo {
  id: string;
  username: string;
  role: string;
  totp_enabled: boolean;
  created_at: string;
  updated_at: string;
}

type ActiveAction =
  | { type: 'create' }
  | { type: 'password'; username: string }
  | { type: 'delete'; username: string }
  | { type: 'disable-totp'; username: string }
  | null;

const formatDate = (iso: string): string => {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch { return iso; }
};

const UserManagement: React.FC = () => {
  const { user } = useUser();
  const { locale } = useLocale();
  const t = translate(locale);

  if (user?.role !== 'superadmin') return <Navigate to="/" replace />;

  const [users, setUsers] = useState<UserInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState<{ kind: 'success' | 'error'; text: string } | null>(null);
  const [action, setAction] = useState<ActiveAction>(null);
  const [formPassword, setFormPassword] = useState('');
  const [formUsername, setFormUsername] = useState('');
  const [disablePassword, setDisablePassword] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    const res = await apiClient.get<UserInfo[]>('/auth/users');
    if (res.ok) setUsers(res.data);
    setLoading(false);
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const resetAction = () => {
    setAction(null);
    setFormPassword('');
    setFormUsername('');
    setDisablePassword('');
    setActionError(null);
  };

  const startAction = (a: ActiveAction) => {
    resetAction();
    setAction(a);
  };

  const handleCreateUser = async () => {
    if (!PASSWORD_PATTERN.test(formPassword) || !formUsername) return;
    setActionLoading(true);
    setActionError(null);
    const res = await apiClient.post<UserInfo>('/auth/users', { username: formUsername, password: formPassword });
    setActionLoading(false);
    if (res.ok) {
      resetAction();
      setNotification({ kind: 'success', text: t.settings.users.createSuccess });
      loadUsers();
    } else {
      setActionError(res.error.startsWith('User already exists') ? t.settings.users.userAlreadyExists : res.error);
    }
  };

  const handleChangePassword = async (username: string) => {
    if (!PASSWORD_PATTERN.test(formPassword)) return;
    setActionLoading(true);
    setActionError(null);
    const res = await apiClient.post<{ message: string }>(`/auth/users/${username}/password`, { password: formPassword });
    setActionLoading(false);
    if (res.ok) {
      resetAction();
      setNotification({ kind: 'success', text: t.settings.users.passwordChangeSuccess });
    } else {
      setActionError(res.error);
    }
  };

  const handleDeleteUser = async (username: string) => {
    setActionLoading(true);
    setActionError(null);
    const res = await apiClient.delete<{ message: string }>(`/auth/users/${username}`);
    setActionLoading(false);
    if (res.ok) {
      resetAction();
      setNotification({ kind: 'success', text: t.settings.users.deleteSuccess });
      loadUsers();
    } else {
      setActionError(res.error === 'Cannot delete yourself' ? t.settings.users.cannotDeleteSelf : res.error);
    }
  };

  const handleDisableTotp = async (username: string) => {
    setActionLoading(true);
    setActionError(null);
    const isSelf = user?.username === username;
    const res = await apiClient.post<{ message: string }>('/auth/totp/disable', {
      password: disablePassword,
      ...(isSelf ? {} : { username }),
    });
    setActionLoading(false);
    if (res.ok) {
      resetAction();
      setNotification({ kind: 'success', text: t.settings.account.totp.disableSuccess });
      loadUsers();
    } else {
      const msg = res.error === 'Invalid password' ? t.settings.account.totp.invalidPassword : res.error;
      setActionError(msg);
    }
  };

  const allPassed = PASSWORD_PATTERN.test(formPassword);

  const policyLabels = [
    { key: 'len', label: t.passwordChange.policy.minLength, test: (pw: string) => pw.length >= 8 },
    { key: 'upper', label: t.passwordChange.policy.uppercase, test: (pw: string) => /[A-Z]/.test(pw) },
    { key: 'lower', label: t.passwordChange.policy.lowercase, test: (pw: string) => /[a-z]/.test(pw) },
    { key: 'digit', label: t.passwordChange.policy.digit, test: (pw: string) => /\d/.test(pw) },
    { key: 'special', label: t.passwordChange.policy.special, test: (pw: string) => /[!@#$%^&*()_+\-=\[\]{}|;:'",.<>?/`~\\]/.test(pw) },
  ];

  const renderChecklist = () => (
    <ul className="um__checklist">
      {policyLabels.map((c) => {
        const passed = c.test(formPassword);
        return (
          <li key={c.key} className={`um__check ${passed ? 'um__check--pass' : ''}`}>
            {passed ? <Checkmark size={16} /> : <Close size={16} />}
            <span>{c.label}</span>
          </li>
        );
      })}
    </ul>
  );

  const headers = [
    { key: 'username', header: t.settings.users.username },
    { key: 'role', header: t.settings.users.role },
    { key: 'totp_enabled', header: t.settings.users.totpStatus },
    { key: 'created_at', header: t.settings.users.createdAt },
    { key: 'actions', header: '' },
  ];

  const rows = users.map((u) => ({
    id: u.id, username: u.username, role: u.role,
    totp_enabled: u.totp_enabled, created_at: u.created_at, actions: u.username,
  }));

  return (
    <div className="um">
      {notification && (
        <InlineNotification kind={notification.kind} title={notification.text}
          onCloseButtonClick={() => setNotification(null)} lowContrast className="um__notification" />
      )}

      {/* Action panels — above table, full width in Grid */}
      {action?.type === 'create' && (
        <Grid className="um__action-grid">
          <Column lg={16} md={8} sm={4}>
            <div className="um__action-panel">
              <h4 className="um__action-title">{t.settings.users.addUserTitle}</h4>
              {actionError && <InlineNotification kind="error" title={actionError} lowContrast hideCloseButton />}
              <Stack gap={4}>
                <TextInput id="create-username" labelText={t.settings.users.username}
                  placeholder={t.settings.users.usernamePlaceholder}
                  value={formUsername} onChange={(e) => setFormUsername(e.target.value)} size="sm" autoFocus />
                <div className="um__password-row">
                  <PasswordInput id="create-password" labelText={t.settings.users.newPassword}
                    placeholder={t.settings.users.newPasswordPlaceholder}
                    value={formPassword} onChange={(e) => setFormPassword(e.target.value)} size="sm" />
                  <Button kind="ghost" size="sm" renderIcon={Renew} hasIconOnly
                    iconDescription={t.settings.users.generatePassword}
                    onClick={() => setFormPassword(generatePassword())} />
                </div>
                {renderChecklist()}
                <div className="um__action-buttons">
                  <Button kind="primary" size="sm" onClick={handleCreateUser}
                    disabled={actionLoading || !formUsername || !allPassed}>
                    {actionLoading ? t.loadingSpinner.loading : t.settings.users.confirm}
                  </Button>
                  <Button kind="ghost" size="sm" onClick={resetAction}>{t.settings.users.cancel}</Button>
                </div>
              </Stack>
            </div>
          </Column>
        </Grid>
      )}

      {action?.type === 'password' && (
        <Grid className="um__action-grid">
          <Column lg={16} md={8} sm={4}>
            <div className="um__action-panel">
              <h4 className="um__action-title">{t.settings.users.changePasswordTitle}: {action.username}</h4>
              {actionError && <InlineNotification kind="error" title={actionError} lowContrast hideCloseButton />}
              <Stack gap={4}>
                <div className="um__password-row">
                  <PasswordInput id="change-password" labelText={t.settings.users.newPassword}
                    placeholder={t.settings.users.newPasswordPlaceholder}
                    value={formPassword} onChange={(e) => setFormPassword(e.target.value)} size="sm" autoFocus />
                  <Button kind="ghost" size="sm" renderIcon={Renew} hasIconOnly
                    iconDescription={t.settings.users.generatePassword}
                    onClick={() => setFormPassword(generatePassword())} />
                </div>
                {renderChecklist()}
                <div className="um__action-buttons">
                  <Button kind="primary" size="sm" onClick={() => handleChangePassword(action.username)}
                    disabled={actionLoading || !allPassed}>
                    {actionLoading ? t.loadingSpinner.loading : t.settings.users.confirm}
                  </Button>
                  <Button kind="ghost" size="sm" onClick={resetAction}>{t.settings.users.cancel}</Button>
                </div>
              </Stack>
            </div>
          </Column>
        </Grid>
      )}

      {action?.type === 'delete' && (
        <Grid className="um__action-grid">
          <Column lg={16} md={8} sm={4}>
            <div className="um__action-panel um__action-panel--danger">
              <h4 className="um__action-title">{t.settings.users.deleteUserTitle}</h4>
              {actionError && <InlineNotification kind="error" title={actionError} lowContrast hideCloseButton />}
              <p className="um__confirm-text">
                <strong>{action.username}</strong> {t.settings.users.confirmDelete}
              </p>
              <div className="um__action-buttons">
                <Button kind="danger" size="sm" onClick={() => handleDeleteUser(action.username)}
                  disabled={actionLoading}>
                  {actionLoading ? t.loadingSpinner.loading : t.settings.users.confirm}
                </Button>
                <Button kind="ghost" size="sm" onClick={resetAction}>{t.settings.users.cancel}</Button>
              </div>
            </div>
          </Column>
        </Grid>
      )}

      {action?.type === 'disable-totp' && (
        <Grid className="um__action-grid">
          <Column lg={16} md={8} sm={4}>
            <div className="um__action-panel um__action-panel--danger">
              <h4 className="um__action-title">{t.settings.account.totp.disableTitle}: {action.username}</h4>
              {actionError && <InlineNotification kind="error" title={actionError} lowContrast hideCloseButton />}
              <Stack gap={4}>
                <p className="um__confirm-text">{t.settings.account.totp.passwordRequired}</p>
                <PasswordInput id="disable-totp-pw" labelText={t.settings.account.totp.confirmPassword}
                  value={disablePassword} onChange={(e) => setDisablePassword(e.target.value)} size="sm" autoFocus />
                <div className="um__action-buttons">
                  <Button kind="danger" size="sm" onClick={() => handleDisableTotp(action.username)}
                    disabled={actionLoading || !disablePassword}>
                    {actionLoading ? t.loadingSpinner.loading : t.settings.users.confirm}
                  </Button>
                  <Button kind="ghost" size="sm" onClick={resetAction}>{t.settings.users.cancel}</Button>
                </div>
              </Stack>
            </div>
          </Column>
        </Grid>
      )}

      <DataTable rows={rows} headers={headers}>
        {({ rows: tableRows, headers: tableHeaders, getHeaderProps, getRowProps, getTableProps, getTableContainerProps }) => (
          <TableContainer {...getTableContainerProps()}>
            <TableToolbar>
              <TableToolbarContent>
                <Button renderIcon={Add} size="sm" kind="primary"
                  onClick={() => startAction({ type: 'create' })}>
                  {t.settings.users.addUser}
                </Button>
              </TableToolbarContent>
            </TableToolbar>
            <Table {...getTableProps()} size="lg">
              <TableHead>
                <TableRow>
                  {tableHeaders.map((header) => {
                    const { key: _key, ...headerProps } = getHeaderProps({ header });
                    return <TableHeader key={header.key} {...headerProps}>{header.header}</TableHeader>;
                  })}
                </TableRow>
              </TableHead>
              <TableBody>
                {tableRows.map((row) => {
                  const { key: _key, ...rowProps } = getRowProps({ row });
                  return (
                    <TableRow key={row.id} {...rowProps}>
                      {row.cells.map((cell) => {
                        const ck = cell.id.split(':')[1];
                        if (ck === 'role') {
                          const role = cell.value as string;
                          return (
                            <TableCell key={cell.id}>
                              <Tag type={role === 'superadmin' ? 'purple' : 'blue'} size="sm">
                                {role === 'superadmin' ? t.settings.users.superadmin : t.settings.users.admin}
                              </Tag>
                            </TableCell>
                          );
                        }
                        if (ck === 'totp_enabled') {
                          return (
                            <TableCell key={cell.id}>
                              <Tag type={cell.value ? 'green' : 'cool-gray'} size="sm">
                                {cell.value ? t.settings.account.totp.enabled : t.settings.account.totp.disabled}
                              </Tag>
                            </TableCell>
                          );
                        }
                        if (ck === 'created_at') return <TableCell key={cell.id}>{formatDate(cell.value as string)}</TableCell>;
                        if (ck === 'actions') {
                          const username = cell.value as string;
                          const isSelf = user?.username === username;
                          const target = users.find((u) => u.username === username);
                          const isSA = target?.role === 'superadmin';
                          const hasTotp = target?.totp_enabled;
                          return (
                            <TableCell key={cell.id}>
                              <OverflowMenu size="sm" flipped>
                                <OverflowMenuItem itemText={t.settings.users.changePassword}
                                  onClick={() => startAction({ type: 'password', username })} />
                                <OverflowMenuItem itemText={t.settings.account.totp.disable}
                                  disabled={!hasTotp}
                                  onClick={() => startAction({ type: 'disable-totp', username })} />
                                <OverflowMenuItem itemText={t.settings.users.deleteUser} isDelete
                                  disabled={isSelf || isSA}
                                  onClick={() => startAction({ type: 'delete', username })} />
                              </OverflowMenu>
                            </TableCell>
                          );
                        }
                        if (ck === 'username') {
                          const username = cell.value as string;
                          const isSelf = user?.username === username;
                          return (
                            <TableCell key={cell.id}>
                              {username}
                              {isSelf && <Tag type="blue" size="sm" style={{ marginLeft: '0.5rem' }}>{t.settings.users.you}</Tag>}
                            </TableCell>
                          );
                        }
                        return <TableCell key={cell.id}>{cell.value}</TableCell>;
                      })}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </DataTable>

      {loading && <p style={{ color: 'var(--cds-text-secondary)', marginTop: '1rem' }}>{t.loadingSpinner.loading}</p>}
    </div>
  );
};

export default UserManagement;
