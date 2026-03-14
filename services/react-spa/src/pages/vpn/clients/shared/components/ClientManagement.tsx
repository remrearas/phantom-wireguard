import React, { useState, useCallback, useEffect, useRef } from 'react';
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
  TableToolbarSearch,
  Button,
  OverflowMenu,
  OverflowMenuItem,
  InlineNotification,
  Pagination,
} from '@carbon/react';
import { Add } from '@carbon/icons-react';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import { apiClient } from '@shared/api/client';
import { formatDateTime } from '@shared/utils/dateUtils';
import TableLoader from '@shared/components/data/TableLoader';
import CreateClientModal from './modals/CreateClientModal';
import RevokeClientModal from './modals/RevokeClientModal';
import ClientConfigModal from './modals/ClientConfigModal';
import ClientKeysModal from './modals/ClientKeysModal';
import './styles/ClientManagement.scss';

// ── Types ─────────────────────────────────────────────────────────

interface ClientSummary {
  id: string;
  name: string;
  ipv4_address: string;
  ipv6_address: string;
  public_key_hex: string;
  created_at: string;
  updated_at: string;
}

interface ClientListResponse {
  clients: ClientSummary[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  order: string;
}

type ActiveAction =
  | { type: 'create' }
  | { type: 'config'; name: string }
  | { type: 'keys'; name: string }
  | { type: 'revoke'; name: string }
  | null;

const COLUMN_COUNT = 6; // 5 data cols + 1 actions col
const SEARCH_DEBOUNCE_MS = 400;

// ── Helpers ───────────────────────────────────────────────────────

const truncateKey = (key: string): string =>
  key.length > 20 ? `${key.slice(0, 8)}…${key.slice(-8)}` : key;

// ── Component ─────────────────────────────────────────────────────

const ClientManagement: React.FC = () => {
  const { locale } = useLocale();
  const t = translate(locale);

  // ── Server state ────────────────────────────────────────────
  const [data, setData] = useState<ClientListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(25);
  const [search, setSearch] = useState('');

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Modal state ─────────────────────────────────────────────
  const [notification, setNotification] = useState<{
    kind: 'success' | 'error';
    text: string;
  } | null>(null);
  const [action, setAction] = useState<ActiveAction>(null);

  // ── Fetch ────────────────────────────────────────────────────
  const fetchClients = useCallback(async (p: number, l: number, s: string) => {
    setLoading(true);
    const params = new URLSearchParams();
    params.set('page', String(p));
    params.set('limit', String(l));
    params.set('order', 'asc');
    if (s) params.set('search', s);

    const res = await apiClient.get<ClientListResponse>(
      `/api/core/clients/list?${params.toString()}`
    );
    if (res.ok) setData(res.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    void fetchClients(page, limit, search);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, limit, fetchClients]);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement> | string) => {
    const value = typeof e === 'string' ? e : e.target.value;
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setPage(1);
      void fetchClients(1, limit, value);
    }, SEARCH_DEBOUNCE_MS);
  };

  const handlePaginationChange = ({
    page: p,
    pageSize: ps,
  }: {
    page: number;
    pageSize: number;
  }) => {
    setPage(p);
    setLimit(ps);
  };

  // ── Actions ──────────────────────────────────────────────────
  const closeAction = () => setAction(null);

  const handleSuccess = (text: string) => {
    setAction(null);
    setNotification({ kind: 'success', text });
    void fetchClients(page, limit, search);
  };

  // ── Table rows ───────────────────────────────────────────────
  const clients = data?.clients ?? [];

  const headers = [
    { key: 'name', header: t.clients.name },
    { key: 'ipv4', header: t.clients.ipv4 },
    { key: 'ipv6', header: t.clients.ipv6 },
    { key: 'public_key', header: t.clients.publicKey },
    { key: 'created_at', header: t.clients.createdAt },
  ];

  const rows = clients.map((c) => ({
    id: c.id,
    name: c.name,
    ipv4: c.ipv4_address,
    ipv6: c.ipv6_address,
    public_key: truncateKey(c.public_key_hex),
    created_at: formatDateTime(c.created_at),
  }));

  // ── Initial skeleton ─────────────────────────────────────────
  if (loading && !data) {
    return (
      <Grid>
        <Column lg={16} md={8} sm={4}>
          <TableLoader columnCount={COLUMN_COUNT} rowCount={8} showToolbar />
        </Column>
      </Grid>
    );
  }

  return (
    <>
      {/* Modals */}
      <CreateClientModal
        open={action?.type === 'create'}
        t={t}
        onClose={closeAction}
        onSuccess={() => handleSuccess(t.clients.createSuccess)}
      />
      <ClientConfigModal
        open={action?.type === 'config'}
        clientName={action?.type === 'config' ? action.name : ''}
        t={t}
        onClose={closeAction}
      />
      <ClientKeysModal
        open={action?.type === 'keys'}
        clientName={action?.type === 'keys' ? action.name : ''}
        t={t}
        onClose={closeAction}
      />
      <RevokeClientModal
        open={action?.type === 'revoke'}
        clientName={action?.type === 'revoke' ? action.name : ''}
        t={t}
        onClose={closeAction}
        onSuccess={() => handleSuccess(t.clients.revokeSuccess)}
      />

      {/* Notification — full-width row */}
      {notification && (
        <Grid>
          <Column lg={16} md={8} sm={4}>
            <InlineNotification
              kind={notification.kind}
              title={notification.text}
              onCloseButtonClick={() => setNotification(null)}
              lowContrast
              className="clients__notification"
              data-testid="vpn-cl-notification"
            />
          </Column>
        </Grid>
      )}

      {/* Table */}
      <Grid>
        <Column lg={16} md={8} sm={4}>
          <div className="clients">
            <DataTable rows={rows} headers={headers}>
              {({
                rows: tableRows,
                headers: tableHeaders,
                getTableProps,
                getHeaderProps,
                getRowProps,
                getTableContainerProps,
              }) => (
                <TableContainer {...getTableContainerProps()}>
                  <TableToolbar>
                    <TableToolbarContent>
                      <TableToolbarSearch
                        persistent
                        placeholder={t.clients.filterName}
                        value={search}
                        onChange={handleSearch}
                      />
                      <Button
                        renderIcon={Add}
                        size="sm"
                        kind="primary"
                        onClick={() => setAction({ type: 'create' })}
                        data-testid="vpn-cl-add-client"
                      >
                        {t.clients.addClient}
                      </Button>
                    </TableToolbarContent>
                  </TableToolbar>

                  {loading ? (
                    <TableLoader
                      columnCount={COLUMN_COUNT}
                      rowCount={Math.min(limit, 10)}
                      showToolbar={false}
                      showHeader={false}
                    />
                  ) : (
                    <Table {...getTableProps()} size="md" data-testid="vpn-cl-table">
                      <TableHead>
                        <TableRow>
                          {tableHeaders.map((header) => {
                            const { key: _key, ...hProps } = getHeaderProps({ header });
                            return (
                              <TableHeader key={header.key} {...hProps}>
                                {header.header}
                              </TableHeader>
                            );
                          })}
                          <TableHeader key="actions-header" />
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {tableRows.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={COLUMN_COUNT}>
                              <p
                                style={{
                                  padding: '1rem 0',
                                  color: 'var(--cds-text-secondary)',
                                  textAlign: 'center',
                                  margin: 0,
                                }}
                              >
                                {t.clients.noClients}
                              </p>
                            </TableCell>
                          </TableRow>
                        ) : (
                          tableRows.map((row) => {
                            const { key: _key, ...rProps } = getRowProps({ row });
                            const clientName = row.cells.find((c) => c.id.endsWith(':name'))
                              ?.value as string;
                            return (
                              <TableRow key={row.id} {...rProps} data-testid={`vpn-cl-row-${clientName}`}>
                                {row.cells.map((cell) => (
                                  <TableCell key={cell.id}>{cell.value as string}</TableCell>
                                ))}
                                <TableCell key={`${row.id}-actions`}>
                                  <OverflowMenu size="sm" flipped data-testid={`vpn-cl-overflow-${clientName}`}>
                                    <OverflowMenuItem
                                      itemText={t.clients.getConfig}
                                      data-testid={`vpn-cl-action-config-${clientName}`}
                                      onClick={() =>
                                        setAction({ type: 'config', name: clientName })
                                      }
                                    />
                                    <OverflowMenuItem
                                      itemText={t.clients.getKeys}
                                      data-testid={`vpn-cl-action-keys-${clientName}`}
                                      onClick={() => setAction({ type: 'keys', name: clientName })}
                                    />
                                    <OverflowMenuItem
                                      itemText={t.clients.revokeClient}
                                      isDelete
                                      data-testid={`vpn-cl-action-revoke-${clientName}`}
                                      onClick={() =>
                                        setAction({ type: 'revoke', name: clientName })
                                      }
                                    />
                                  </OverflowMenu>
                                </TableCell>
                              </TableRow>
                            );
                          })
                        )}
                      </TableBody>
                    </Table>
                  )}

                  {/* Localized pagination */}
                  <Pagination
                    totalItems={data?.total ?? 0}
                    pageSize={limit}
                    page={page}
                    pageSizes={[10, 25, 50, 100]}
                    backwardText={t.pagination.backwardText}
                    forwardText={t.pagination.forwardText}
                    itemsPerPageText={t.pagination.itemsPerPageText}
                    itemRangeText={(min, max, total) =>
                      `${min}–${max} ${t.pagination.ofText} ${total} ${t.pagination.itemsText}`
                    }
                    pageRangeText={(current, total) =>
                      `${current} ${t.pagination.ofText} ${total} ${t.pagination.pagesText}`
                    }
                    onChange={handlePaginationChange}
                  />
                </TableContainer>
              )}
            </DataTable>
          </div>
        </Column>
      </Grid>
    </>
  );
};

export default ClientManagement;
