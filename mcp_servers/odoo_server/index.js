import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// ── Mock Odoo Data Store ────────────────────────────────────────────
const mockData = {
  contacts: [
    { id: 1, name: "Client A", email: "clienta@example.com", phone: "+1-555-0101", type: "customer" },
    { id: 2, name: "Client B", email: "clientb@example.com", phone: "+1-555-0102", type: "customer" },
    { id: 3, name: "Supplier X", email: "supplierx@example.com", phone: "+1-555-0201", type: "vendor" },
  ],
  invoices: [
    { id: 1001, partner: "Client A", amount: 2500.00, date: "2026-02-01", status: "paid", due_date: "2026-03-01" },
    { id: 1002, partner: "Client B", amount: 3500.00, date: "2026-02-10", status: "open", due_date: "2026-03-10" },
    { id: 1003, partner: "Client A", amount: 1200.00, date: "2026-02-20", status: "draft", due_date: "2026-03-20" },
  ],
  payments: [
    { id: 2001, invoice_id: 1001, amount: 2500.00, date: "2026-02-15", method: "bank_transfer", status: "posted" },
  ],
  nextInvoiceId: 1004,
  nextPaymentId: 2002,
  nextContactId: 4,
};

// ── Create MCP Server ───────────────────────────────────────────────
const server = new Server(
  { name: "odoo-mcp-server", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

// ── List Tools ──────────────────────────────────────────────────────
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "create_invoice",
      description: "Create a new invoice in Odoo",
      inputSchema: {
        type: "object",
        properties: {
          partner: { type: "string", description: "Customer/partner name" },
          lines: {
            type: "array",
            description: "Invoice line items",
            items: {
              type: "object",
              properties: {
                description: { type: "string" },
                quantity: { type: "number" },
                unit_price: { type: "number" },
              },
              required: ["description", "quantity", "unit_price"],
            },
          },
          date: { type: "string", description: "Invoice date (YYYY-MM-DD)" },
        },
        required: ["partner", "lines"],
      },
    },
    {
      name: "get_invoices",
      description: "Get invoices from Odoo, optionally filtered by status",
      inputSchema: {
        type: "object",
        properties: {
          status: { type: "string", description: "Filter by status: draft, open, paid, all", default: "all" },
        },
      },
    },
    {
      name: "create_payment",
      description: "Record a payment for an invoice in Odoo",
      inputSchema: {
        type: "object",
        properties: {
          invoice_id: { type: "number", description: "Invoice ID to pay" },
          amount: { type: "number", description: "Payment amount" },
          method: { type: "string", description: "Payment method (bank_transfer, cash, credit_card)", default: "bank_transfer" },
        },
        required: ["invoice_id", "amount"],
      },
    },
    {
      name: "get_contacts",
      description: "Get all contacts (customers and vendors) from Odoo",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "create_contact",
      description: "Create a new contact in Odoo",
      inputSchema: {
        type: "object",
        properties: {
          name: { type: "string", description: "Contact name" },
          email: { type: "string", description: "Email address" },
          phone: { type: "string", description: "Phone number" },
          type: { type: "string", description: "Contact type: customer or vendor", default: "customer" },
        },
        required: ["name", "email"],
      },
    },
    {
      name: "get_account_balance",
      description: "Get current account balances from Odoo",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "get_financial_summary",
      description: "Get a financial summary for a given period",
      inputSchema: {
        type: "object",
        properties: {
          period: { type: "string", description: "Period: this_month, last_month, this_quarter", default: "this_month" },
        },
      },
    },
  ],
}));

// ── Handle Tool Calls ───────────────────────────────────────────────
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "create_invoice": {
        const total = args.lines.reduce((sum, l) => sum + l.quantity * l.unit_price, 0);
        const invoice = {
          id: mockData.nextInvoiceId++,
          partner: args.partner,
          amount: total,
          date: args.date || new Date().toISOString().split("T")[0],
          status: "draft",
          due_date: "", // would calculate from payment terms
          lines: args.lines,
        };
        mockData.invoices.push(invoice);
        return {
          content: [{ type: "text", text: `Invoice created! ID: ${invoice.id}, Amount: $${total.toFixed(2)}, Partner: ${args.partner}` }],
        };
      }

      case "get_invoices": {
        const status = args?.status || "all";
        const filtered = status === "all"
          ? mockData.invoices
          : mockData.invoices.filter((i) => i.status === status);
        const lines = filtered.map(
          (i) => `- #${i.id} | ${i.partner} | $${i.amount.toFixed(2)} | ${i.status} | ${i.date}`
        );
        return {
          content: [{ type: "text", text: `Invoices (${status}):\n${lines.join("\n")}` }],
        };
      }

      case "create_payment": {
        const invoice = mockData.invoices.find((i) => i.id === args.invoice_id);
        if (!invoice) {
          return { content: [{ type: "text", text: `Invoice #${args.invoice_id} not found` }], isError: true };
        }
        const payment = {
          id: mockData.nextPaymentId++,
          invoice_id: args.invoice_id,
          amount: args.amount,
          date: new Date().toISOString().split("T")[0],
          method: args.method || "bank_transfer",
          status: "posted",
        };
        mockData.payments.push(payment);
        invoice.status = "paid";
        return {
          content: [{ type: "text", text: `Payment recorded! ID: ${payment.id}, Amount: $${args.amount.toFixed(2)}, Invoice: #${args.invoice_id}` }],
        };
      }

      case "get_contacts": {
        const lines = mockData.contacts.map(
          (c) => `- ${c.name} (${c.type}) | ${c.email} | ${c.phone}`
        );
        return {
          content: [{ type: "text", text: `Contacts:\n${lines.join("\n")}` }],
        };
      }

      case "create_contact": {
        const contact = {
          id: mockData.nextContactId++,
          name: args.name,
          email: args.email,
          phone: args.phone || "",
          type: args.type || "customer",
        };
        mockData.contacts.push(contact);
        return {
          content: [{ type: "text", text: `Contact created! ID: ${contact.id}, Name: ${contact.name}` }],
        };
      }

      case "get_account_balance": {
        const totalReceivable = mockData.invoices
          .filter((i) => i.status === "open" || i.status === "draft")
          .reduce((sum, i) => sum + i.amount, 0);
        const totalReceived = mockData.payments
          .filter((p) => p.status === "posted")
          .reduce((sum, p) => sum + p.amount, 0);

        return {
          content: [{
            type: "text",
            text: `Account Balance:\n- Bank Balance: $${(totalReceived + 15000).toFixed(2)}\n- Accounts Receivable: $${totalReceivable.toFixed(2)}\n- Total Received (this period): $${totalReceived.toFixed(2)}`,
          }],
        };
      }

      case "get_financial_summary": {
        const totalInvoiced = mockData.invoices.reduce((sum, i) => sum + i.amount, 0);
        const totalPaid = mockData.invoices.filter((i) => i.status === "paid").reduce((sum, i) => sum + i.amount, 0);
        const totalOpen = mockData.invoices.filter((i) => i.status === "open").reduce((sum, i) => sum + i.amount, 0);
        const totalDraft = mockData.invoices.filter((i) => i.status === "draft").reduce((sum, i) => sum + i.amount, 0);

        return {
          content: [{
            type: "text",
            text: `Financial Summary (${args?.period || "this_month"}):\n- Total Invoiced: $${totalInvoiced.toFixed(2)}\n- Paid: $${totalPaid.toFixed(2)}\n- Open: $${totalOpen.toFixed(2)}\n- Draft: $${totalDraft.toFixed(2)}\n- Collection Rate: ${totalInvoiced > 0 ? ((totalPaid / totalInvoiced) * 100).toFixed(1) : 0}%`,
          }],
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

// ── Start Server ────────────────────────────────────────────────────
const transport = new StdioServerTransport();
await server.connect(transport);
