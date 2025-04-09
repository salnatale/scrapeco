import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: {
      main: '#09D3AC'
    },
    background: {
      default: '#0E1117',
      paper: '#1B1B1B'
    },
    text: {
      primary: '#FFFFFF',
      secondary: '#EEEEEE'
    }
  },
  typography: {
    fontFamily: 'Roboto, Helvetica, Arial, sans-serif',
    h1: {
      fontWeight: 700,
      fontSize: '3rem'
    },
    h2: {
      fontWeight: 600,
      fontSize: '2rem'
    },
    body1: {
      fontSize: '1.1rem'
    }
  }
});

export default theme;
