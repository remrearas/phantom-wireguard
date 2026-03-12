import React from 'react';
import { Toggletip, ToggletipButton, ToggletipContent } from '@carbon/react';
import { Information } from '@carbon/icons-react';
import { useLocale } from '@shared/hooks';
import { translate } from '@shared/translations';
import './styles/formula-info.scss';

const FormulaInfo: React.FC = () => {
  const { locale } = useLocale();
  const t = translate(locale);
  const f = t.documentation.formulaInfo as Record<string, string>;

  return (
    <div className="formula-info" data-testid="docs-formula-info">
      <div className="formula-info__row">
        <code className="formula-info__formula">∀i ∈ [2, n−2] : v4_net[i] ↔ v6_net[i]</code>
        <Toggletip align="right">
          <ToggletipButton label={f.pairingLabel}>
            <Information />
          </ToggletipButton>
          <ToggletipContent>
            <div className="formula-info__content">
              <p className="formula-info__title">{f.pairingTitle}</p>
              <ul className="formula-info__list">
                <li><code>∀</code> — {f.forAll}</li>
                <li><code>i ∈ [2, n−2]</code> — {f.range}</li>
                <li><code>2</code> — {f.indexTwo}</li>
                <li><code>n−2</code> — {f.indexNMinus2}</li>
                <li><code>v4_net[i] ↔ v6_net[i]</code> — {f.bijection}</li>
              </ul>
            </div>
          </ToggletipContent>
        </Toggletip>
      </div>

      <div className="formula-info__row">
        <code className="formula-info__formula">|Assigned_IPv4| ≡ |Assigned_IPv6|</code>
        <Toggletip align="right">
          <ToggletipButton label={f.symmetryLabel}>
            <Information />
          </ToggletipButton>
          <ToggletipContent>
            <div className="formula-info__content">
              <p className="formula-info__title">{f.symmetryTitle}</p>
              <ul className="formula-info__list">
                <li><code>|...|</code> — {f.cardinality}</li>
                <li><code>≡</code> — {f.identical}</li>
              </ul>
              <p className="formula-info__summary">{f.symmetrySummary}</p>
            </div>
          </ToggletipContent>
        </Toggletip>
      </div>
    </div>
  );
};

export default FormulaInfo;
