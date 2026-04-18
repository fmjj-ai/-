export const formatPreviewCellValue = (value: unknown) => {
  if (value === null || value === undefined || value === '') {
    return ''
  }

  if (typeof value === 'boolean') {
    return value ? 1 : 0
  }

  return value
}
