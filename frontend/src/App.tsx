import React, { useState, useEffect } from 'react';
import './App.css';
import { 
  Activity, 
  ArrowRight, 
  Globe, 
  Wallet,
  FileText,
  Search,
  ChevronRight,
  Zap,
  Calendar,
  TrendingUp,
  RefreshCw
} from 'lucide-react';
import axios from 'axios';

// --- Types ---
interface Indicator {
  label: string;
  value: number;
  unit: string;
  change: number;
  status: 'safe' | 'warning' | 'danger';
}

interface LogicStep {
  label: string;
  change: string;
}

interface CausalChain {
  id: string;
  category: string;
  tags: string[];
  title: string;
  description: string;
  raw_shock: string;
  raw_shock_rationale?: string;
  logic_steps: LogicStep[];
  wallet_hit: string;
  transmission: string;
  transmission_rationale?: string;
  magnitude?: string;
  monthly_impact?: number;
  created_at?: string;
}

const API_BASE = 'http://localhost:8000/api';

function App() {
  const [activeTab, setActiveTab] = useState('NOW');
  const [indicators, setIndicators] = useState<Indicator[]>([]);
  const [chains, setChains] = useState<CausalChain[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get(`${API_BASE}/dashboard`);
        setIndicators(res.data.indicators);
        setChains(res.data.chains);
      } catch (err) {
        console.error("Failed to fetch data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [activeTab]); // 탭 바뀔 때 새로고침

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'danger': return 'var(--danger-color)';
      case 'warning': return 'var(--warning-color)';
      default: return 'var(--safe-color)';
    }
  };

  const formatDate = (dateStr?: string) => {
      if (!dateStr) return '';
      const d = new Date(dateStr);
      return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
  };

  return (
    <div className="app-container">
      <header className="header">
        <div className="logo">THE INSIGHT</div>
        <nav className="nav">
          {['NOW', 'WHY', 'LIFE', 'SEARCH'].map(tab => (
            <div 
              key={tab} 
              className={`nav-item ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </div>
          ))}
        </nav>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <button 
            className="refresh-btn" 
            onClick={() => {
                setLoading(true);
                const fetchData = async () => {
                    try {
                        const res = await axios.get(`${API_BASE}/dashboard`);
                        setIndicators(res.data.indicators);
                        setChains(res.data.chains);
                    } catch (err) {
                        console.error("Failed to fetch data", err);
                    } finally {
                        setLoading(false);
                    }
                };
                fetchData();
            }}
            title="데이터 새로고침"
          >
            <RefreshCw size={18} className={loading ? 'spinning' : ''} />
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
            <Activity size={14} color="var(--safe-color)" />
            Live Connected
          </div>
        </div>
      </header>

      <main className="main-content">
        {loading ? (
            <div style={{ textAlign: 'center', padding: '5rem', color: 'var(--text-secondary)' }}>분석 엔진 연결 중...</div>
        ) : (
          <>
            {activeTab === 'NOW' && (
              <>
                <h2 className="section-title"><Zap size={20} color="var(--accent-color)" /> 실시간 주요 지표</h2>
                <div className="indicators-grid">
                  {indicators.map((ind, i) => (
                    <div key={i} className="indicator-card">
                      <div className="indicator-label">{ind.label}</div>
                      <div className="indicator-value-row">
                        <span className="indicator-value">{ind.value.toLocaleString()}</span>
                        <span className={`indicator-change ${ind.change >= 0 ? 'up' : 'down'}`}>{ind.change >= 0 ? '+' : ''}{ind.change}</span>
                      </div>
                      <div style={{ marginTop: '12px', height: '3px', borderRadius: '2px', background: `linear-gradient(90deg, ${getStatusColor(ind.status)} 0%, transparent 100%)`, width: '60%' }}></div>
                    </div>
                  ))}
                </div>

                <h2 className="section-title"><Globe size={20} color="var(--accent-color)" /> 오늘의 헤드라인</h2>
                {chains.map(chain => (
                  <div key={chain.id} className="causal-card" onClick={() => setActiveTab('WHY')} style={{ cursor: 'pointer' }}>
                    <div className="causal-header">
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                           <span className="category-tag">{chain.category.toUpperCase()}</span>
                           <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                             <Calendar size={12} /> {formatDate(chain.created_at)}
                           </span>
                        </div>
                        <div className="causal-title">{chain.title}</div>
                      </div>
                      <ChevronRight size={20} color="var(--text-secondary)" style={{ marginLeft: '1rem' }} />
                    </div>
                    <p className="causal-desc">{chain.description}</p>
                    <div style={{ marginTop: '20px', padding: '15px', background: 'rgba(255,255,255,0.03)', borderRadius: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                       <div style={{ color: 'var(--danger-color)', fontWeight: 700 }}>원료비 {chain.raw_shock}</div>
                       <ArrowRight size={16} color="var(--text-secondary)" />
                       <div style={{ color: 'var(--accent-color)', fontWeight: 700 }}>지갑 영향 {chain.wallet_hit}</div>
                    </div>
                  </div>
                ))}
              </>
            )}

            {activeTab === 'WHY' && (
              <>
                <h2 className="section-title"><FileText size={20} color="var(--accent-color)" /> 심층 인과관계 체인</h2>
                {chains.map(chain => (
                  <div key={chain.id} className="causal-card">
                    <div className="causal-header">
                        <span className="category-tag">{chain.category.toUpperCase()} | {chain.magnitude || 'Medium'} Risk</span>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>분석 시점: {formatDate(chain.created_at)}</span>
                    </div>
                    <h3 style={{ fontSize: '1.8rem', marginBottom: '2rem', fontWeight: 800 }}>{chain.title}</h3>
                    
                    {/* [UPGRADED] Multi-step Logic Chain */}
                    <div className="logic-chain-container">
                       {chain.logic_steps && chain.logic_steps.length > 0 ? (
                           chain.logic_steps.map((step, idx) => (
                               <React.Fragment key={idx}>
                                   <div className="logic-step-node">
                                       <div className="node-label">{step.label}</div>
                                       <div className={`node-change ${step.change.includes('-') ? 'down' : 'up'}`}>
                                           {step.change}
                                       </div>
                                   </div>
                                   {idx < chain.logic_steps.length - 1 && (
                                       <div className="logic-step-dash"><ArrowRight size={20} /></div>
                                   )}
                               </React.Fragment>
                           ))
                       ) : (
                           <div style={{ color: 'var(--text-secondary)', padding: '20px' }}>단계별 인과관계 분석 데이터를 불러오는 중입니다...</div>
                       )}
                    </div>

                    <div style={{ marginTop: '30px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
                        <div className="indicator-card" style={{ borderLeft: '4px solid var(--accent-color)' }}>
                            <div className="indicator-label"><Wallet size={16} /> 예상 월 가계 부담</div>
                            <div className="indicator-value" style={{ color: 'var(--accent-color)', fontSize: '2.2rem', marginTop: '0.5rem' }}>
                                +{chain.monthly_impact?.toLocaleString()}원
                            </div>
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.8rem' }}>
                                * 4인 가구 평균 월 지출액 기준 추산 (전이 시차 {chain.transmission} 예정)
                            </p>
                        </div>
                        <div className="indicator-card">
                            <div className="indicator-label"><TrendingUp size={16} /> 인과관계 요약</div>
                            <p style={{ fontSize: '0.9rem', lineHeight: 1.7, marginTop: '0.8rem' }}>{chain.description}</p>
                        </div>
                    </div>
                  </div>
                ))}
              </>
            )}

            {activeTab === 'LIFE' && (
              <div className="causal-card" style={{ textAlign: 'center', padding: '5rem 2rem' }}>
                <Wallet size={64} color="var(--accent-color)" style={{ marginBottom: '2rem' }} />
                <h2 style={{ fontSize: '1.5rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>이번 달 예상 추가 지출 합계</h2>
                <div style={{ fontSize: '4.5rem', fontWeight: 900, color: 'var(--danger-color)', letterSpacing: '-3px', marginBottom: '1rem' }}>
                  +{chains.reduce((acc, curr) => acc + (curr.monthly_impact || 0), 0).toLocaleString()}원
                </div>
                <p style={{ marginTop: '2.5rem', color: 'var(--text-secondary)', maxWidth: '600px', margin: '2.5rem auto 0', lineHeight: 1.8 }}>
                  현재 시스템에서 분석된 팩터들에 따르면, 글로벌 공급망 불안과 지정학적 리스크의 결합으로 인해 <br/>
                  평균적인 가구 경제에서 <strong>월 {chains.reduce((acc, curr) => acc + (curr.monthly_impact || 0), 0).toLocaleString()}원</strong> 수준의 실질 부담 증가가 예상됩니다.
                </p>
              </div>
            )}

            {activeTab === 'SEARCH' && (
              <div style={{ textAlign: 'center', padding: '10rem 2rem', color: 'var(--text-secondary)', background: 'var(--card-bg)', borderRadius: '20px' }}>
                <Search size={48} style={{ marginBottom: '1.5rem', opacity: 0.3 }} />
                <h3 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>기사 시맨틱 검색</h3>
                <p>Phase 3에서 모든 원본 뉴스를 자연어로 검색하고 <br/>관련 인과관계를 즉시 찾아주는 검색 기능이 제공될 예정입니다.</p>
              </div>
            )}
          </>
        )}
      </main>

      <footer style={{ padding: '3rem', textAlign: 'center', borderTop: '1px solid var(--card-border)', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
        &copy; 2026 THE INSIGHT. All rights reserved. | <span style={{ color: 'var(--safe-color)' }}>●</span> Systems Nominal (Phase 3 Prep)
      </footer>
    </div>
  );
}

export default App;
