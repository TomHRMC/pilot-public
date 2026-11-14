/**
 * Jest mock for expo-file-system/legacy
 *
 * Location: apps/mobile/__mocks__/expo-file-system-legacy.js
 *
 * expo-file-system v19 moved legacy APIs (writeAsStringAsync, readAsStringAsync,
 * uploadAsync, cacheDirectory, EncodingType, FileSystemUploadType) to the
 * /legacy sub-path.  This sub-path has .d.ts types but no compiled .js file
 * that Node.js/Jest can require() directly.
 *
 * The moduleNameMapper entry in package.json points
 * "^expo-file-system/legacy$" → this file so Jest can resolve the import
 * in DisabledAccountExportScreen.tsx and photo-upload.ts during tests.
 *
 * All functions are jest.fn() stubs with sensible defaults.
 */

module.exports = {
  __esModule: true,
  // Readable/writable file APIs
  writeAsStringAsync: jest.fn().mockResolvedValue(undefined),
  readAsStringAsync: jest.fn().mockResolvedValue(""),
  copyAsync: jest.fn().mockResolvedValue(undefined),
  moveAsync: jest.fn().mockResolvedValue(undefined),
  deleteAsync: jest.fn().mockResolvedValue(undefined),
  makeDirectoryAsync: jest.fn().mockResolvedValue(undefined),
  getInfoAsync: jest
    .fn()
    .mockResolvedValue({ exists: true, isDirectory: false, size: 0 }),
  uploadAsync: jest
    .fn()
    .mockResolvedValue({ status: 200, headers: {}, body: "" }),
  downloadAsync: jest
    .fn()
    .mockResolvedValue({ status: 200, headers: {}, uri: "" }),
  // Common constants
  cacheDirectory: "/tmp/ExponentFileSystem/cache/",
  documentDirectory: "/tmp/ExponentFileSystem/documents/",
  bundleDirectory: "/tmp/ExponentFileSystem/bundle/",
  // Enums
  EncodingType: {
    UTF8: "utf8",
    Base64: "base64",
  },
  FileSystemUploadType: {
    BINARY_CONTENT: 0,
    MULTIPART: 1,
  },
  FileSystemSessionType: {
    BACKGROUND: 1,
    FOREGROUND: 0,
  },
};
