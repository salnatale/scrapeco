import { createTheme } from '@mui/material/styles';

// Modern dark theme with cleanly contrasting colors
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#3CDFFF', // Bright cyan blue
      light: '#72E8FF',
      dark: '#00B2D6',
      contrastText: '#121212'
    },
    secondary: {
      main: '#FF5FA2', // Bright pink
      light: '#FF8DC1',
      dark: '#D13B7A',
      contrastText: '#121212'
    },
    error: {
      main: '#FF6B6B', // Brighter red
    },
    warning: {
      main: '#FFD166', // Bright yellow
    },
    info: {
      main: '#5C7CFA', // Blue
    },
    success: {
      main: '#69DB7C', // Bright green
    },
    background: {
      default: '#0F172A', // Dark blue-black
      paper: '#1A2338', // Slightly lighter blue-black
      card: '#25314D' // Highlight areas
    },
    text: {
      primary: '#FFFFFF',
      secondary: '#B8C2CC',
      disabled: '#64748B'
    },
    divider: 'rgba(255, 255, 255, 0.12)'
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 700,
      fontSize: '3rem',
      lineHeight: 1.2,
      letterSpacing: '-0.01562em'
    },
    h2: {
      fontWeight: 600,
      fontSize: '2.5rem',
      lineHeight: 1.3,
      letterSpacing: '-0.00833em'
    },
    h3: {
      fontWeight: 600,
      fontSize: '2rem',
      lineHeight: 1.4,
      letterSpacing: '0em'
    },
    h4: {
      fontWeight: 600,
      fontSize: '1.5rem',
      lineHeight: 1.4,
      letterSpacing: '0.00735em'
    },
    h5: {
      fontWeight: 600,
      fontSize: '1.25rem',
      lineHeight: 1.5,
      letterSpacing: '0em'
    },
    h6: {
      fontWeight: 600,
      fontSize: '1rem',
      lineHeight: 1.6,
      letterSpacing: '0.0075em'
    },
    subtitle1: {
      fontSize: '1rem',
      lineHeight: 1.75,
      letterSpacing: '0.00938em'
    },
    subtitle2: {
      fontSize: '0.875rem',
      fontWeight: 500,
      lineHeight: 1.57,
      letterSpacing: '0.00714em'
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.5,
      letterSpacing: '0.00938em'
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.43,
      letterSpacing: '0.01071em'
    },
    button: {
      fontWeight: 600,
      fontSize: '0.875rem',
      lineHeight: 1.75,
      letterSpacing: '0.02857em',
      textTransform: 'none'
    }
  },
  shape: {
    borderRadius: 12
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          padding: '8px 16px',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 4px 8px rgba(0, 0, 0, 0.2)'
          }
        },
        contained: {
          '&:hover': {
            boxShadow: '0 6px 12px rgba(0, 0, 0, 0.25)'
          }
        }
      }
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)'
        }
      }
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none'
        },
        elevation1: {
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)'
        },
        elevation2: {
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
        }
      }
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 10px rgba(0, 0, 0, 0.15)'
        }
      }
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6
        }
      }
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          fontSize: '0.9rem'
        }
      }
    }
  }
});

export default theme;
