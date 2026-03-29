import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

type ItemRecord = Record<string, unknown>;

const DEFAULT_PAGE_SIZE = 500;
const DEFAULT_OUTPUT_PATH = "exports/items.csv";

function getRequiredEnv(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }

  return value;
}

function normalizeBaseUrl(rawBaseUrl: string): string {
  return rawBaseUrl.replace(/\/+$/, "").replace(/\/desk$/, "");
}

function buildAuthHeader(): string {
  const apiKey = getRequiredEnv("ERPNEXT_API_KEY");
  const apiSecret = getRequiredEnv("ERPNEXT_API_SECRET");

  return `token ${apiKey}:${apiSecret}`;
}

function escapeCsvValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }

  const serialized =
    typeof value === "object" ? JSON.stringify(value) : String(value);

  if (/[",\n]/.test(serialized)) {
    return `"${serialized.replace(/"/g, "\"\"")}"`;
  }

  return serialized;
}

async function fetchItemPage(
  baseUrl: string,
  authHeader: string,
  limitStart: number,
  pageSize: number,
): Promise<ItemRecord[]> {
  const url = new URL(`${baseUrl}/api/resource/Item`);
  url.searchParams.set("fields", JSON.stringify(["*"]));
  url.searchParams.set("limit_page_length", String(pageSize));
  url.searchParams.set("limit_start", String(limitStart));
  url.searchParams.set("order_by", "name asc");

  const response = await fetch(url, {
    headers: {
      Authorization: authHeader,
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(
      `ERPNext API request failed (${response.status} ${response.statusText}): ${body}`,
    );
  }

  const payload = (await response.json()) as { data?: ItemRecord[] };

  if (!Array.isArray(payload.data)) {
    throw new Error("ERPNext API response did not contain a data array.");
  }

  return payload.data;
}

function collectHeaders(records: ItemRecord[]): string[] {
  const headers: string[] = [];
  const seen = new Set<string>();

  for (const record of records) {
    for (const key of Object.keys(record)) {
      if (!seen.has(key)) {
        seen.add(key);
        headers.push(key);
      }
    }
  }

  return headers;
}

function buildCsv(records: ItemRecord[], headers: string[]): string {
  const rows = [
    headers.join(","),
    ...records.map((record) =>
      headers.map((header) => escapeCsvValue(record[header])).join(","),
    ),
  ];

  return `${rows.join("\n")}\n`;
}

async function main(): Promise<void> {
  const outputArg = process.argv[2]?.trim();
  const outputPath = outputArg || DEFAULT_OUTPUT_PATH;
  const rawBaseUrl = getRequiredEnv("ERPNEXT_BASE_URL");
  const baseUrl = normalizeBaseUrl(rawBaseUrl);
  const authHeader = buildAuthHeader();

  const allRecords: ItemRecord[] = [];
  let limitStart = 0;

  while (true) {
    const page = await fetchItemPage(
      baseUrl,
      authHeader,
      limitStart,
      DEFAULT_PAGE_SIZE,
    );

    if (page.length === 0) {
      break;
    }

    allRecords.push(...page);
    limitStart += page.length;

    if (page.length < DEFAULT_PAGE_SIZE) {
      break;
    }
  }

  if (allRecords.length === 0) {
    throw new Error("No Item records were returned from ERPNext.");
  }

  const headers = collectHeaders(allRecords);
  const csv = buildCsv(allRecords, headers);
  const absoluteOutputPath = path.resolve(outputPath);

  await mkdir(path.dirname(absoluteOutputPath), { recursive: true });
  await writeFile(absoluteOutputPath, csv, "utf8");

  console.log(
    JSON.stringify(
      {
        outputPath: absoluteOutputPath,
        itemCount: allRecords.length,
        columnCount: headers.length,
      },
      null,
      2,
    ),
  );
}

void main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(message);
  process.exitCode = 1;
});
