import React from 'react';
import { DataTableSkeleton } from '@carbon/react';

interface TableLoaderProps {
  columnCount?: number;
  rowCount?: number;
  showHeader?: boolean;
  showToolbar?: boolean;
}

const TableLoader: React.FC<TableLoaderProps> = ({
  columnCount = 5,
  rowCount = 10,
  showHeader = true,
  showToolbar = true,
}) => {
  return (
    <DataTableSkeleton
      columnCount={columnCount}
      rowCount={rowCount}
      showHeader={showHeader}
      showToolbar={showToolbar}
      zebra={false}
    />
  );
};

export default TableLoader;
