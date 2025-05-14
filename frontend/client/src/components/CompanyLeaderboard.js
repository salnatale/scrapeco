// frontend/client/src/components/CompanyLeaderboard.js
import React, { useState } from 'react';
import {
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Box,
  Typography,
  Chip,
  Avatar,
  IconButton,
  Tooltip,
  LinearProgress
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  Info as InfoIcon,
  Visibility as ViewIcon
} from '@mui/icons-material';

const CompanyLeaderboard = ({ companies = [] }) => {
  const [orderBy, setOrderBy] = useState('recentTransitions');
  const [order, setOrder] = useState('desc');

  const handleRequestSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const sortedCompanies = React.useMemo(() => {
    return [...companies].sort((a, b) => {
      let aVal = a[orderBy] || 0;
      let bVal = b[orderBy] || 0;
      
      if (order === 'desc') {
        return bVal - aVal;
      }
      return aVal - bVal;
    });
  }, [companies, order, orderBy]);

  const getGrowthTrend = (transitions) => {
    if (transitions > 10) return { icon: <TrendingUp color="success" />, color: 'success' };
    if (transitions < 5) return { icon: <TrendingDown color="error" />, color: 'error' };
    return { icon: <TrendingUp color="warning" />, color: 'warning' };
  };

  const columns = [
    { 
      id: 'name', 
      label: 'Company', 
      sortable: false,
      render: (company) => (
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Avatar sx={{ mr: 2, bgcolor: 'primary.main' }}>
            {company.name?.charAt(0)}
          </Avatar>
          <Box>
            <Typography variant="subtitle2" fontWeight={600}>
              {company.name || 'Unknown Company'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {company.industry || 'Technology'}
            </Typography>
          </Box>
        </Box>
      )
    },
    {
      id: 'employeeCount',
      label: 'Employees',
      sortable: true,
      render: (company) => (
        <Typography variant="body2">
          {company.employeeCount || 0}
        </Typography>
      )
    },
    {
      id: 'recentTransitions',
      label: 'Recent Hires (3M)',
      sortable: true,
      render: (company) => {
        const trend = getGrowthTrend(company.recentTransitions);
        return (
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Typography variant="body2" sx={{ mr: 1 }}>
              {company.recentTransitions || 0}
            </Typography>
            {trend.icon}
          </Box>
        );
      }
    },
    {
      id: 'growthRate',
      label: 'Growth Rate',
      sortable: true,
      render: (company) => {
        const rate = company.growthRate || 0;
        const color = rate > 10 ? 'success' : rate > 5 ? 'warning' : 'default';
        return (
          <Chip
            label={`${rate.toFixed(1)}%`}
            size="small"
            color={color}
            variant="outlined"
          />
        );
      }
    },
    {
      id: 'churnRate',
      label: 'Churn Rate',
      sortable: true,
      render: (company) => {
        const rate = company.churnRate || 0;
        return (
          <Box sx={{ width: 100 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="caption" sx={{ minWidth: 35 }}>
                {rate.toFixed(1)}%
              </Typography>
              <Box sx={{ width: '100%', mr: 1 }}>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(rate, 25) * 4} // Scale to 0-100 for visual
                  color={rate > 15 ? 'error' : rate > 10 ? 'warning' : 'success'}
                  sx={{ height: 8, borderRadius: 5 }}
                />
              </Box>
            </Box>
          </Box>
        );
      }
    },
    {
      id: 'actions',
      label: 'Actions',
      sortable: false,
      render: (company) => (
        <Box>
          <Tooltip title="View Details">
            <IconButton size="small" color="primary">
              <ViewIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Company Info">
            <IconButton size="small">
              <InfoIcon />
            </IconButton>
          </Tooltip>
        </Box>
      )
    }
  ];

  if (!companies.length) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary">
          No companies found
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Try adjusting your filters or search criteria
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper elevation={2} sx={{ backgroundColor: 'background.paper' }}>
      <Box sx={{ p: 3, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" fontWeight={600}>
          Company Leaderboard
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Showing {companies.length} companies ranked by talent metrics
        </Typography>
      </Box>

      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              {columns.map((column) => (
                <TableCell key={column.id}>
                  {column.sortable ? (
                    <TableSortLabel
                      active={orderBy === column.id}
                      direction={orderBy === column.id ? order : 'asc'}
                      onClick={() => handleRequestSort(column.id)}
                    >
                      {column.label}
                    </TableSortLabel>
                  ) : (
                    column.label
                  )}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {sortedCompanies.map((company, index) => (
              <TableRow key={company.urn || index} hover>
                {columns.map((column) => (
                  <TableCell key={column.id}>
                    {column.render(company)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
};

export default CompanyLeaderboard;