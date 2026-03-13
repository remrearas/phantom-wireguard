import React, { useState } from 'react';
import {
  Grid,
  Column,
  Tag,
  Button,
  CopyButton,
  StructuredListWrapper,
  StructuredListBody,
  StructuredListRow,
  StructuredListCell,
} from '@carbon/react';
import { Power } from '@carbon/icons-react';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import DisableGhostModal from './modals/DisableGhostModal';
import './styles/ghost.scss';

export interface GhostStatusData {
  enabled: boolean;
  running: boolean;
  bind_url: string;
  restrict_to: string;
  restrict_path_prefix: string;
  tls_configured: boolean;
}

interface Props {
  status: GhostStatusData;
  onDisabled: () => Promise<void>;
}

const GhostStatus: React.FC<Props> = ({ status, onDisabled }) => {
  const { locale } = useLocale();
  const t = translate(locale);
  const tg = t.ghost;

  const [modalOpen, setModalOpen] = useState(false);

  return (
    <div className="ghost-status">
      <Grid>
        <Column xlg={16} lg={16} md={8} sm={4}>
          <div className="ghost-status__card">
            <div className="ghost-status__header">
              <div className="ghost-status__tags">
                <Tag
                  type={status.running ? 'green' : 'red'}
                  size="md"
                  data-testid="ghost-status-running"
                >
                  {status.running ? tg.running : tg.stopped}
                </Tag>
                <Tag type="teal" size="md" data-testid="ghost-status-enabled">
                  {tg.enabled}
                </Tag>
                {status.tls_configured && (
                  <Tag type="blue" size="md" data-testid="ghost-status-tls">
                    {tg.tlsConfigured}
                  </Tag>
                )}
              </div>
            </div>

            <StructuredListWrapper className="ghost-status__list">
              <StructuredListBody>
                <StructuredListRow>
                  <StructuredListCell noWrap>{tg.bindUrl}</StructuredListCell>
                  <StructuredListCell>
                    <div
                      className="ghost-status__copy-row"
                      data-testid="ghost-status-bind-url"
                    >
                      <code>{status.bind_url}</code>
                      <CopyButton
                        onClick={() =>
                          void navigator.clipboard.writeText(status.bind_url)
                        }
                        iconDescription={t.settings.account.totp.copied}
                      />
                    </div>
                  </StructuredListCell>
                </StructuredListRow>

                <StructuredListRow>
                  <StructuredListCell noWrap>{tg.restrictPath}</StructuredListCell>
                  <StructuredListCell>
                    <div
                      className="ghost-status__copy-row"
                      data-testid="ghost-status-path-prefix"
                    >
                      <code>{status.restrict_path_prefix}</code>
                      <CopyButton
                        onClick={() =>
                          void navigator.clipboard.writeText(
                            status.restrict_path_prefix
                          )
                        }
                        iconDescription={t.settings.account.totp.copied}
                      />
                    </div>
                  </StructuredListCell>
                </StructuredListRow>

                <StructuredListRow>
                  <StructuredListCell noWrap>{tg.restrictTo}</StructuredListCell>
                  <StructuredListCell data-testid="ghost-status-restrict-to">
                    <code>{status.restrict_to}</code>
                  </StructuredListCell>
                </StructuredListRow>
                <StructuredListRow>
                  <StructuredListCell />
                  <StructuredListCell>
                    <Button
                      kind="danger"
                      renderIcon={Power}
                      onClick={() => setModalOpen(true)}
                      data-testid="ghost-disable-btn"
                    >
                      {tg.disable}
                    </Button>
                  </StructuredListCell>
                </StructuredListRow>
              </StructuredListBody>
            </StructuredListWrapper>
          </div>
        </Column>
      </Grid>

      <DisableGhostModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onDisabled={() => {
          setModalOpen(false);
          void onDisabled();
        }}
      />
    </div>
  );
};

export default GhostStatus;
