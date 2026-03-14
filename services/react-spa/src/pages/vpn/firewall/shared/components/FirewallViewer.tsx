import React, { useState, useCallback, useEffect } from 'react';
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
  OverflowMenu,
  OverflowMenuItem,
  Tag,
} from '@carbon/react';
import { Renew } from '@carbon/icons-react';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import { apiClient } from '@shared/api/client';
import TableLoader from '@shared/components/data/TableLoader';
import GroupDetailModal from './modals/GroupDetailModal';
import RawTableModal from './modals/RawTableModal';
import './styles/FirewallViewer.scss';

// ── Types ─────────────────────────────────────────────────────────

interface GroupRecord {
  id: number;
  name: string;
  group_type: string;
  enabled: boolean;
  priority: number;
  metadata: Record<string, unknown>;
  created_at: number;
  updated_at: number;
}

// ── Constants ─────────────────────────────────────────────────────

const COLUMN_COUNT = 5; // 4 data cols + 1 actions col

// ── Component ─────────────────────────────────────────────────────

const FirewallViewer: React.FC = () => {
  const { locale } = useLocale();
  const t = translate(locale);

  const [groups, setGroups] = useState<GroupRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [rawTableOpen, setRawTableOpen] = useState(false);

  // ── Fetch ─────────────────────────────────────────────────────
  const fetchGroups = useCallback(async () => {
    setLoading(true);
    const res = await apiClient.get<GroupRecord[]>('/api/core/firewall/groups/list');
    if (res.ok) setGroups(res.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    void fetchGroups();
  }, [fetchGroups]);

  // ── Initial skeleton ──────────────────────────────────────────
  if (loading && groups.length === 0) {
    return (
      <Grid>
        <Column lg={16} md={8} sm={4}>
          <TableLoader columnCount={COLUMN_COUNT} rowCount={6} showToolbar />
        </Column>
      </Grid>
    );
  }

  // ── Table data ────────────────────────────────────────────────
  const headers = [
    { key: 'name', header: t.firewall.name },
    { key: 'group_type', header: t.firewall.type },
    { key: 'enabled', header: t.firewall.enabled },
    { key: 'priority', header: t.firewall.priority },
  ];

  const rows = groups.map((g) => ({
    id: String(g.id),
    name: g.name,
    group_type: g.group_type,
    enabled: g.enabled,
    priority: g.priority,
  }));

  const groupsMap = new Map(groups.map((g) => [String(g.id), g]));

  return (
    <>
      <Grid>
        <Column lg={16} md={8} sm={4}>
          <div className="firewall">
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
                      <Button
                        renderIcon={Renew}
                        size="sm"
                        kind="ghost"
                        iconDescription={t.firewall.refresh}
                        hasIconOnly
                        onClick={() => void fetchGroups()}
                        disabled={loading}
                        data-testid="vpn-fw-refresh"
                      />
                    </TableToolbarContent>
                  </TableToolbar>

                  {loading ? (
                    <TableLoader
                      columnCount={COLUMN_COUNT}
                      rowCount={Math.min(groups.length || 4, 10)}
                      showToolbar={false}
                      showHeader={false}
                    />
                  ) : (
                    <Table {...getTableProps()} size="md" data-testid="vpn-fw-table">
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
                              <p className="firewall__empty">{t.firewall.noGroups}</p>
                            </TableCell>
                          </TableRow>
                        ) : (
                          tableRows.map((row) => {
                            const { key: _key, ...rProps } = getRowProps({ row });
                            const group = groupsMap.get(row.id)!;
                            return (
                              <TableRow
                                key={row.id}
                                {...rProps}
                                data-testid={`vpn-fw-row-${group.name}`}
                              >
                                {row.cells.map((cell) => {
                                  if (cell.info.header === 'enabled') {
                                    return (
                                      <TableCell key={cell.id}>
                                        <Tag
                                          type={cell.value ? 'green' : 'red'}
                                          size="sm"
                                        >
                                          {cell.value ? t.firewall.active : t.firewall.inactive}
                                        </Tag>
                                      </TableCell>
                                    );
                                  }
                                  return (
                                    <TableCell key={cell.id}>
                                      {cell.value as string}
                                    </TableCell>
                                  );
                                })}
                                <TableCell key={`${row.id}-actions`}>
                                  <OverflowMenu
                                    size="sm"
                                    flipped
                                    data-testid={`vpn-fw-overflow-${group.name}`}
                                  >
                                    <OverflowMenuItem
                                      itemText={t.firewall.viewDetails}
                                      onClick={() => setSelectedGroup(group.name)}
                                      data-testid={`vpn-fw-action-details-${group.name}`}
                                    />
                                    <OverflowMenuItem
                                      itemText={t.firewall.viewRawTable}
                                      onClick={() => setRawTableOpen(true)}
                                      data-testid={`vpn-fw-action-raw-${group.name}`}
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
                </TableContainer>
              )}
            </DataTable>
          </div>
        </Column>
      </Grid>

      <GroupDetailModal
        groupName={selectedGroup}
        onClose={() => setSelectedGroup(null)}
      />

      <RawTableModal
        open={rawTableOpen}
        onClose={() => setRawTableOpen(false)}
      />
    </>
  );
};

export default FirewallViewer;
