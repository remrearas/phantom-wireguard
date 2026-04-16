import React from 'react';
import { DataTableSkeleton } from '@carbon/react';
import './styles/TableLoader.scss';

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
    <div className="table-loader">
      <DataTableSkeleton
        columnCount={columnCount}
        rowCount={rowCount}
        showHeader={showHeader}
        showToolbar={showToolbar}
        zebra={false}
      />
    </div>
  );
};

export default TableLoader;
