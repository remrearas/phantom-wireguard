import React, { useState, useCallback, useEffect } from 'react';
import {
  Grid,
  Column,
  Tile,
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
  Modal,
  StructuredListWrapper,
  StructuredListBody,
  StructuredListRow,
  StructuredListCell,
} from '@carbon/react';
import { Renew } from '@carbon/icons-react';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import { apiClient } from '@shared/api/client';
import TableLoader from '@shared/components/data/TableLoader';
import './styles/wireguard.scss';

// ── Types ─────────────────────────────────────────────────────────

interface InterfaceInfo {
  public_key: string;
  listen_port: number;
  fwmark: number;
}

interface PeerInfo {
  public_key: string;
  name: string | null;
  endpoint: string;
  allowed_ips: string[];
  latest_handshake: number;
  rx_bytes: number;
  tx_bytes: number;
  keepalive: number;
}

interface WireGuardStatusData {
  interface: InterfaceInfo;
  peers: PeerInfo[];
  total_peers: number;
}

type PeerStatus = 'online' | 'offline' | 'never';

// ── Constants ─────────────────────────────────────────────────────

const COLUMN_COUNT = 7; // 6 data cols + 1 actions col
const ONLINE_THRESHOLD_SECS = 180;

// ── Helpers ───────────────────────────────────────────────────────

const truncateKey = (key: string): string =>
  key.length > 20 ? `${key.slice(0, 8)}…${key.slice(-8)}` : key;

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
};

const getStatus = (ts: number): PeerStatus => {
  if (ts === 0) return 'never';
  return Date.now() / 1000 - ts < ONLINE_THRESHOLD_SECS ? 'online' : 'offline';
};

const formatHandshake = (ts: number): string => {
  if (ts === 0) return '—';
  const secs = Math.floor(Date.now() / 1000 - ts);
  if (secs < 60) return `${secs}s`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h`;
  return `${Math.floor(secs / 86400)}d`;
};

const peerKey = (peer: PeerInfo): string => peer.name ?? peer.public_key.slice(0, 8);

// ── Component ─────────────────────────────────────────────────────

const WireGuardStatus: React.FC = () => {
  const { locale } = useLocale();
  const t = translate(locale);

  const [data, setData] = useState<WireGuardStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<PeerInfo | null>(null);
  const [refreshingPeer, setRefreshingPeer] = useState<string | null>(null);

  // ── Fetch ─────────────────────────────────────────────────────
  const fetchStatus = useCallback(async () => {
    setLoading(true);
    const res = await apiClient.get<WireGuardStatusData>('/api/core/wireguard');
    if (res.ok) setData(res.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    void fetchStatus();
  }, [fetchStatus]);

  // ── Per-peer refresh ──────────────────────────────────────────
  const handleRefreshPeer = async (name: string) => {
    setRefreshingPeer(name);
    const res = await apiClient.post<PeerInfo>('/api/core/wireguard/peer', { name });
    if (res.ok && data) {
      setData({
        ...data,
        peers: data.peers.map((p) => (p.name === name ? res.data : p)),
      });
    }
    setRefreshingPeer(null);
  };

  // ── Initial skeleton ──────────────────────────────────────────
  if (loading && !data) {
    return (
      <Grid>
        <Column lg={16} md={8} sm={4}>
          <TableLoader columnCount={COLUMN_COUNT} rowCount={8} showToolbar />
        </Column>
      </Grid>
    );
  }

  // ── Table data ────────────────────────────────────────────────
  const peers = data?.peers ?? [];
  const peersMap = new Map(peers.map((p) => [p.public_key, p]));

  const headers = [
    { key: 'status', header: t.wireguard.status },
    { key: 'name', header: t.wireguard.name },
    { key: 'endpoint', header: t.wireguard.endpoint },
    { key: 'last_handshake', header: t.wireguard.lastHandshake },
    { key: 'rx', header: t.wireguard.rxBytes },
    { key: 'tx', header: t.wireguard.txBytes },
  ];

  const rows = peers.map((p) => ({
    id: p.public_key,
    status: getStatus(p.latest_handshake) as string,
    name: p.name ?? t.wireguard.unknown,
    endpoint: p.endpoint || '—',
    last_handshake: formatHandshake(p.latest_handshake),
    rx: formatBytes(p.rx_bytes),
    tx: formatBytes(p.tx_bytes),
  }));

  // ── Detail modal helpers ───────────────────────────────────────
  const statusTagType = (s: PeerStatus) =>
    s === 'online' ? 'green' : s === 'offline' ? 'red' : 'gray';
  const statusTagText = (s: PeerStatus) =>
    s === 'online'
      ? t.wireguard.online
      : s === 'offline'
        ? t.wireguard.offline
        : t.wireguard.neverConnected;

  return (
    <>
      {/* Interface card */}
      <Grid>
        <Column lg={16} md={8} sm={4}>
          <Tile className="wireguard__interface" data-testid="vpn-wg-interface">
            <p className="wireguard__interface-title">{t.wireguard.interfaceTitle}</p>
            <div className="wireguard__interface-kv-grid">
              <div className="wireguard__kv">
                <span className="wireguard__kv-label">{t.wireguard.publicKey}</span>
                <span className="wireguard__kv-value">
                  {truncateKey(data?.interface.public_key ?? '')}
                </span>
              </div>
              <div className="wireguard__kv">
                <span className="wireguard__kv-label">{t.wireguard.listenPort}</span>
                <span className="wireguard__kv-value">{data?.interface.listen_port}</span>
              </div>
              <div className="wireguard__kv">
                <span className="wireguard__kv-label">{t.wireguard.fwmark}</span>
                <span className="wireguard__kv-value">{data?.interface.fwmark}</span>
              </div>
              <div className="wireguard__kv">
                <span className="wireguard__kv-label">{t.wireguard.totalPeers}</span>
                <span className="wireguard__kv-value">{data?.total_peers}</span>
              </div>
            </div>
          </Tile>
        </Column>
      </Grid>

      {/* Peers table */}
      <Grid>
        <Column lg={16} md={8} sm={4}>
          <div className="wireguard">
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
                        iconDescription={t.wireguard.refresh}
                        hasIconOnly
                        onClick={() => void fetchStatus()}
                        disabled={loading}
                        data-testid="vpn-wg-refresh"
                      />
                    </TableToolbarContent>
                  </TableToolbar>

                  {loading ? (
                    <TableLoader
                      columnCount={COLUMN_COUNT}
                      rowCount={Math.min(peers.length || 5, 10)}
                      showToolbar={false}
                      showHeader={false}
                    />
                  ) : (
                    <Table {...getTableProps()} size="md" data-testid="vpn-wg-table">
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
                                {t.wireguard.noPeers}
                              </p>
                            </TableCell>
                          </TableRow>
                        ) : (
                          tableRows.map((row) => {
                            const { key: _key, ...rProps } = getRowProps({ row });
                            const peer = peersMap.get(row.id)!;
                            const key = peerKey(peer);
                            return (
                              <TableRow key={row.id} {...rProps} data-testid={`vpn-wg-row-${key}`}>
                                {row.cells.map((cell) => {
                                  if (cell.info.header === 'status') {
                                    const s = cell.value as PeerStatus;
                                    return (
                                      <TableCell key={cell.id}>
                                        <Tag type={statusTagType(s) as never} size="sm">
                                          {statusTagText(s)}
                                        </Tag>
                                      </TableCell>
                                    );
                                  }
                                  return (
                                    <TableCell key={cell.id}>{cell.value as string}</TableCell>
                                  );
                                })}
                                <TableCell key={`${row.id}-actions`}>
                                  <OverflowMenu
                                    size="sm"
                                    flipped
                                    data-testid={`vpn-wg-overflow-${key}`}
                                  >
                                    <OverflowMenuItem
                                      itemText={t.wireguard.details}
                                      onClick={() => setDetail(peer)}
                                      data-testid={`vpn-wg-action-details-${key}`}
                                    />
                                    {peer.name && (
                                      <OverflowMenuItem
                                        itemText={
                                          refreshingPeer === peer.name
                                            ? '...'
                                            : t.wireguard.refreshPeer
                                        }
                                        disabled={refreshingPeer === peer.name}
                                        onClick={() =>
                                          peer.name && void handleRefreshPeer(peer.name)
                                        }
                                        data-testid={`vpn-wg-action-refresh-${peer.name}`}
                                      />
                                    )}
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

      {/* Peer detail modal */}
      <Modal
        open={!!detail}
        modalHeading={t.wireguard.peerDetails}
        primaryButtonText={t.wireguard.close}
        onRequestClose={() => setDetail(null)}
        onRequestSubmit={() => setDetail(null)}
        size="sm"
        className="wireguard__modal"
        data-testid="vpn-wg-detail-modal"
      >
        {detail &&
          (() => {
            const s = getStatus(detail.latest_handshake);
            return (
              <Grid>
                <Column lg={16} md={8} sm={4}>
                  <StructuredListWrapper isCondensed>
                    <StructuredListBody>
                      <StructuredListRow>
                        <StructuredListCell>{t.wireguard.status}</StructuredListCell>
                        <StructuredListCell>
                          <Tag type={statusTagType(s) as never} size="sm">
                            {statusTagText(s)}
                          </Tag>
                        </StructuredListCell>
                      </StructuredListRow>
                      <StructuredListRow>
                        <StructuredListCell>{t.wireguard.name}</StructuredListCell>
                        <StructuredListCell>
                          {detail.name ?? t.wireguard.unknown}
                        </StructuredListCell>
                      </StructuredListRow>
                      <StructuredListRow>
                        <StructuredListCell>{t.wireguard.publicKey}</StructuredListCell>
                        <StructuredListCell>
                          <span className="wireguard__detail-mono">{detail.public_key}</span>
                        </StructuredListCell>
                      </StructuredListRow>
                      <StructuredListRow>
                        <StructuredListCell>{t.wireguard.endpoint}</StructuredListCell>
                        <StructuredListCell>
                          <span className="wireguard__detail-mono">{detail.endpoint || '—'}</span>
                        </StructuredListCell>
                      </StructuredListRow>
                      <StructuredListRow>
                        <StructuredListCell>{t.wireguard.allowedIps}</StructuredListCell>
                        <StructuredListCell>
                          <div className="wireguard__allowed-ips">
                            {detail.allowed_ips.length > 0
                              ? detail.allowed_ips.map((ip) => <span key={ip}>{ip}</span>)
                              : '—'}
                          </div>
                        </StructuredListCell>
                      </StructuredListRow>
                      <StructuredListRow>
                        <StructuredListCell>{t.wireguard.lastHandshake}</StructuredListCell>
                        <StructuredListCell>
                          {formatHandshake(detail.latest_handshake)}
                        </StructuredListCell>
                      </StructuredListRow>
                      <StructuredListRow>
                        <StructuredListCell>{t.wireguard.rxBytes}</StructuredListCell>
                        <StructuredListCell>{formatBytes(detail.rx_bytes)}</StructuredListCell>
                      </StructuredListRow>
                      <StructuredListRow>
                        <StructuredListCell>{t.wireguard.txBytes}</StructuredListCell>
                        <StructuredListCell>{formatBytes(detail.tx_bytes)}</StructuredListCell>
                      </StructuredListRow>
                      <StructuredListRow>
                        <StructuredListCell>{t.wireguard.keepalive}</StructuredListCell>
                        <StructuredListCell>
                          {detail.keepalive > 0 ? `${detail.keepalive}s` : '—'}
                        </StructuredListCell>
                      </StructuredListRow>
                    </StructuredListBody>
                  </StructuredListWrapper>
                </Column>
              </Grid>
            );
          })()}
      </Modal>
    </>
  );
};

export default WireGuardStatus;
