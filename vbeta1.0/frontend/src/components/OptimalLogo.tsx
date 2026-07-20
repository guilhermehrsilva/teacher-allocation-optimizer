import React from "react";

export default function OptimalLogo() {
  return (
    <div className="optimal-logo-container" aria-label="OPTIMAL - Alocação Docente">
      <svg
        className="optimal-logo-svg"
        viewBox="0 0 310 60"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="opt-energy" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00F2FE" />
            <stop offset="100%" stopColor="#0072FF" />
          </linearGradient>
          <linearGradient id="opt-ring-dark" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#0A2850" />
            <stop offset="100%" stopColor="#031124" />
          </linearGradient>
          <linearGradient id="opt-ring-glow" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00C6FF" stopOpacity="0.85" />
            <stop offset="50%" stopColor="#0072FF" stopOpacity="0.4" />
            <stop offset="100%" stopColor="#002661" stopOpacity="0.9" />
          </linearGradient>
          <filter id="opt-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
          <filter id="opt-core-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* --- EMBLEMA CIRCULAR SCI-FI (Centrado em X=30, Y=30, Raio=28) --- */}
        <g className="optimal-emblem">
          {/* Anel Externo Fundo */}
          <circle cx="30" cy="30" r="28" fill="url(#opt-ring-dark)" stroke="#0E386C" strokeWidth="1.5" />
          
          {/* Segmentos Cibernéticos Externos (Arcos energizados) */}
          <path
            d="M 6 22 A 26 26 0 0 1 22 6 L 25 10 A 21 21 0 0 0 10 25 Z"
            fill="url(#opt-energy)"
            opacity="0.9"
          />
          <path
            d="M 38 6 A 26 26 0 0 1 54 22 L 50 25 A 21 21 0 0 0 35 10 Z"
            fill="#0090FF"
            opacity="0.8"
          />
          <path
            d="M 54 38 A 26 26 0 0 1 38 54 L 35 50 A 21 21 0 0 0 50 35 Z"
            fill="url(#opt-energy)"
            opacity="0.9"
          />
          <path
            d="M 22 54 A 26 26 0 0 1 6 38 L 10 35 A 21 21 0 0 0 25 50 Z"
            fill="#0072FF"
            opacity="0.8"
          />

          {/* Anel Intermediário de Estrutura */}
          <circle cx="30" cy="30" r="21" fill="#04142B" stroke="#00C6FF" strokeWidth="1" strokeOpacity="0.4" />
          
          {/* Triângulo Externo Invertido */}
          <polygon
            points="12,18 48,18 30,48"
            fill="none"
            stroke="url(#opt-energy)"
            strokeWidth="3.2"
            strokeLinejoin="round"
            filter="url(#opt-glow)"
          />
          {/* Triângulo Interno Invertido preenchido com energia */}
          <polygon
            points="16,21 44,21 30,44"
            fill="url(#opt-energy)"
            opacity="0.25"
          />
          
          {/* Detalhes Tecnológicos Internos (Linhas conectoras) */}
          <line x1="30" y1="9" x2="30" y2="18" stroke="#00D2FF" strokeWidth="1.5" strokeOpacity="0.7" />
          <line x1="12" y1="41" x2="19" y2="33" stroke="#00D2FF" strokeWidth="1.5" strokeOpacity="0.7" />
          <line x1="48" y1="41" x2="41" y2="33" stroke="#00D2FF" strokeWidth="1.5" strokeOpacity="0.7" />

          {/* Núcleo Central Brilhante (Core) */}
          <circle cx="30" cy="28" r="6.5" fill="#04162D" stroke="url(#opt-energy)" strokeWidth="2.5" />
          <circle cx="30" cy="28" r="3.5" fill="#E6FFFF" filter="url(#opt-core-glow)" />
        </g>

        {/* --- TIPOGRAFIA VETORIAL "OPTIMAL" (Estilo Sci-Fi Geométrico Limpo) --- */}
        <g className="optimal-wordmark" fill="#FFFFFF" transform="translate(70, 14)">
          {/* O */}
          <path d="M 12 0 C 4 0 0 5 0 16 C 0 27 4 32 12 32 C 20 32 24 27 24 16 C 24 5 20 0 12 0 Z M 12 5.5 C 17 5.5 18.5 8 18.5 16 C 18.5 24 17 26.5 12 26.5 C 7 26.5 5.5 24 5.5 16 C 5.5 8 7 5.5 12 5.5 Z" />
          
          {/* P */}
          <path d="M 33 0 L 48 0 C 56 0 59 4 59 11 C 59 18 56 22 48 22 L 39 22 L 39 32 L 33 32 L 33 0 Z M 39 5.5 L 39 16.5 L 47.5 16.5 C 51.5 16.5 53 14.5 53 11 C 53 7.5 51.5 5.5 47.5 5.5 L 39 5.5 Z" />
          
          {/* T */}
          <path d="M 66 0 L 92 0 L 92 5.5 L 82 5.5 L 82 32 L 76 32 L 76 5.5 L 66 5.5 L 66 0 Z" />
          
          {/* I */}
          <path d="M 100 0 L 106 0 L 106 32 L 100 32 L 100 0 Z" />
          
          {/* M */}
          <path d="M 115 0 L 121 0 L 129.5 18 L 138 0 L 144 0 L 144 32 L 138.5 32 L 138.5 11 L 131.5 25.5 L 127.5 25.5 L 120.5 11 L 120.5 32 L 115 32 L 115 0 Z" />
          
          {/* A (Futurista com Acento Triângulo Ciano no Centro) */}
          <path d="M 166 0 L 179 32 L 173 32 L 166 14 L 159 32 L 153 32 L 166 0 Z" />
          <polygon points="166,19 169.5,27 162.5,27" fill="#00D2FF" filter="url(#opt-glow)" />
          
          {/* L */}
          <path d="M 188 0 L 194 0 L 194 26.5 L 212 26.5 L 212 32 L 188 32 L 188 0 Z" />
        </g>
      </svg>
    </div>
  );
}
