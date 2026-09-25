import * as XLSX from 'xlsx';

/**
 * Clean client-side Excel exporter using SheetJS.
 * Strictly excludes "Validation Status" and "Validation Score (%)"
 * as requested for client output files, while server retains them in master file.
 * Includes formatted headers, auto-filter, and clickable mailto: anchor links for all emails.
 */
export const exportRecordsToExcel = (records, customFilename = null) => {
  if (!records || records.length === 0) {
    throw new Error('No records available to export.');
  }

  // Exact clean output columns matching Final output.xlsx specification
  const rows = records.map((r, idx) => ({
    'S.No': idx + 1,
    'Contract No': r.contract_no || 'NA',
    'Generated Date': r.generated_date || 'NA',
    'Organisation Name': r.organisation_name || 'NA',
    'Buyer Contact': r.buyer_contact || 'NA',
    'Buyer Email': r.buyer_email || 'NA',
    'Paying Authority Email': r.paying_authority_email || 'NA',
    'Seller Company Name': r.seller_company_name || 'NA',
    'Seller Contact No': r.seller_contact_no || 'NA',
    'Seller Email': r.seller_email || 'NA',
    'Seller GSTIN': r.seller_gstin || 'NA',
    'Seller Address': r.seller_address || 'NA',
    'Products Name': r.product_name || 'NA',
    'Brand': r.brand || 'NA',
    'Category & Quadrant': r.category_name_quadrant || 'NA',
    'Ordered Quantity': r.ordered_quantity || 'NA',
    'Unit Price (INR)': typeof r.unit_price === 'number' ? r.unit_price : parseFloat(r.unit_price) || 0,
    'Total Order Value (INR)': typeof r.total_order_value === 'number' ? r.total_order_value : parseFloat(r.total_order_value) || 0,
    'Consignee Email': r.consignee_email || 'NA',
    'Consignee Contact': r.consignee_contact_no || 'NA',
    'Consignee Address': r.consignee_address || 'NA',
    'File Name': r.file_name || 'NA',
  }));

  const worksheet = XLSX.utils.json_to_sheet(rows);

  // Styling column widths for optimal spreadsheet presentation
  worksheet['!cols'] = [
    { wch: 6 },  // S.No
    { wch: 26 }, // Contract No
    { wch: 16 }, // Generated Date
    { wch: 28 }, // Organisation Name
    { wch: 18 }, // Buyer Contact
    { wch: 28 }, // Buyer Email
    { wch: 28 }, // Paying Authority Email
    { wch: 30 }, // Seller Company Name
    { wch: 18 }, // Seller Contact No
    { wch: 28 }, // Seller Email
    { wch: 18 }, // Seller GSTIN
    { wch: 36 }, // Seller Address
    { wch: 32 }, // Products Name
    { wch: 20 }, // Brand
    { wch: 30 }, // Category & Quadrant
    { wch: 16 }, // Ordered Quantity
    { wch: 18 }, // Unit Price (INR)
    { wch: 22 }, // Total Order Value (INR)
    { wch: 28 }, // Consignee Email
    { wch: 18 }, // Consignee Contact
    { wch: 36 }, // Consignee Address
    { wch: 32 }, // File Name
  ];

  // Set row heights (header row is 28pt, data rows 20pt)
  worksheet['!rows'] = [
    { hpt: 26 },
    ...rows.map(() => ({ hpt: 20 }))
  ];

  // Add clickable mailto: hyperlinks (anchor tags) for all email columns
  const emailKeys = ['Buyer Email', 'Paying Authority Email', 'Seller Email', 'Consignee Email'];
  const headers = Object.keys(rows[0] || {});

  rows.forEach((row, rIdx) => {
    headers.forEach((h, cIdx) => {
      if (emailKeys.includes(h)) {
        const val = row[h];
        if (val && val !== 'NA' && String(val).includes('@')) {
          const cleanEmail = String(val).trim();
          const cellRef = XLSX.utils.encode_cell({ r: rIdx + 1, c: cIdx });
          if (worksheet[cellRef]) {
            worksheet[cellRef].l = {
              Target: `mailto:${cleanEmail}`,
              Tooltip: `Send email to ${cleanEmail}`
            };
          }
        }
      }
    });
  });

  // Enable Auto-Filter across all columns
  if (headers.length > 0 && rows.length > 0) {
    const lastColLetter = XLSX.utils.encode_col(headers.length - 1);
    worksheet['!autofilter'] = {
      ref: `A1:${lastColLetter}${rows.length + 1}`
    };
  }

  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'GeM_Contracts');

  const filename = customFilename || `gem_contracts_${new Date().toISOString().slice(0, 10)}.xlsx`;
  XLSX.writeFile(workbook, filename);
  return true;
};
