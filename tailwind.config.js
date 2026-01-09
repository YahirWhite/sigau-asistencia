/** @type {import('tailwindcss').Config} */
module.exports = {
  // 1. ACTIVAR MODO OSCURO POR CLASE
  darkMode: 'class', 
  
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        azul: {
          inst: '#00205B',  /* Azul Institucional */
          sec: '#0077b6',   /* Azul Secundario */
        },
        amarillo: {
          DEFAULT: '#ffcc00',
          hover: '#e6b800'
        },
        gris: {
          fondo: '#e2e8f0', 
          input: '#f8fafc',  
          texto: '#334155'   
        },
        // 2. COLORES SUGERIDOS PARA MODO OSCURO (Slate/Zinc suelen verse más pro)
        oscuro: {
          fondo: '#0f172a', /* Slate-900 */
          card: '#1e293b',  /* Slate-800 */
          borde: '#334155'  /* Slate-700 */
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}