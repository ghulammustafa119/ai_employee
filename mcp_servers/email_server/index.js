import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { google } from "googleapis";
import { readFileSync } from "fs";
import { resolve } from "path";

// Load Gmail credentials
const CREDENTIALS_PATH = process.env.GMAIL_CREDENTIALS || "credentials.json";
const TOKEN_PATH = process.env.GMAIL_TOKEN || "token.json";

let gmailService = null;

async function getGmailService() {
  if (gmailService) return gmailService;

  const token = JSON.parse(readFileSync(resolve(TOKEN_PATH), "utf-8"));
  const credentials = JSON.parse(
    readFileSync(resolve(CREDENTIALS_PATH), "utf-8")
  );

  const { client_id, client_secret } = credentials.installed || credentials.web;
  const oAuth2Client = new google.auth.OAuth2(client_id, client_secret);
  oAuth2Client.setCredentials(token);

  gmailService = google.gmail({ version: "v1", auth: oAuth2Client });
  return gmailService;
}

function createEmailMessage(to, subject, body) {
  const message = [
    `To: ${to}`,
    `Subject: ${subject}`,
    "Content-Type: text/plain; charset=utf-8",
    "",
    body,
  ].join("\n");

  return Buffer.from(message).toString("base64url");
}

// Create MCP Server
const server = new Server(
  { name: "email-mcp-server", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "send_email",
      description: "Send an email via Gmail",
      inputSchema: {
        type: "object",
        properties: {
          to: { type: "string", description: "Recipient email address" },
          subject: { type: "string", description: "Email subject line" },
          body: { type: "string", description: "Email body text" },
        },
        required: ["to", "subject", "body"],
      },
    },
    {
      name: "draft_email",
      description: "Create a draft email in Gmail (does not send)",
      inputSchema: {
        type: "object",
        properties: {
          to: { type: "string", description: "Recipient email address" },
          subject: { type: "string", description: "Email subject line" },
          body: { type: "string", description: "Email body text" },
        },
        required: ["to", "subject", "body"],
      },
    },
    {
      name: "search_email",
      description: "Search emails in Gmail",
      inputSchema: {
        type: "object",
        properties: {
          query: {
            type: "string",
            description: "Gmail search query (e.g., 'from:user@example.com')",
          },
          max_results: {
            type: "number",
            description: "Maximum results to return",
            default: 10,
          },
        },
        required: ["query"],
      },
    },
  ],
}));

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    const gmail = await getGmailService();

    switch (name) {
      case "send_email": {
        const raw = createEmailMessage(args.to, args.subject, args.body);
        const result = await gmail.users.messages.send({
          userId: "me",
          requestBody: { raw },
        });
        return {
          content: [
            {
              type: "text",
              text: `Email sent successfully! Message ID: ${result.data.id}`,
            },
          ],
        };
      }

      case "draft_email": {
        const raw = createEmailMessage(args.to, args.subject, args.body);
        const result = await gmail.users.drafts.create({
          userId: "me",
          requestBody: { message: { raw } },
        });
        return {
          content: [
            {
              type: "text",
              text: `Draft created! Draft ID: ${result.data.id}`,
            },
          ],
        };
      }

      case "search_email": {
        const result = await gmail.users.messages.list({
          userId: "me",
          q: args.query,
          maxResults: args.max_results || 10,
        });

        const messages = result.data.messages || [];
        const details = [];

        for (const msg of messages.slice(0, 5)) {
          const full = await gmail.users.messages.get({
            userId: "me",
            id: msg.id,
            format: "metadata",
            metadataHeaders: ["From", "Subject", "Date"],
          });
          const headers = {};
          for (const h of full.data.payload.headers) {
            headers[h.name] = h.value;
          }
          details.push(
            `- From: ${headers.From}\n  Subject: ${headers.Subject}\n  Date: ${headers.Date}`
          );
        }

        return {
          content: [
            {
              type: "text",
              text: `Found ${messages.length} emails:\n\n${details.join("\n\n")}`,
            },
          ],
        };
      }

      default:
        return {
          content: [{ type: "text", text: `Unknown tool: ${name}` }],
          isError: true,
        };
    }
  } catch (error) {
    return {
      content: [{ type: "text", text: `Error: ${error.message}` }],
      isError: true,
    };
  }
});

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
