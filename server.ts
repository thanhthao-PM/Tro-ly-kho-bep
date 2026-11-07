import express from 'express';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3000;

app.use(express.json());

// Initialize Gemini API client on the server side
const geminiApiKey = process.env.GEMINI_API_KEY;
let ai: GoogleGenAI | null = null;

if (geminiApiKey) {
  ai = new GoogleGenAI({
    apiKey: geminiApiKey,
    httpOptions: {
      headers: {
        'User-Agent': 'aistudio-build',
      },
    },
  });
}

// Health check
app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', hasGemini: !!ai });
});

// Grounded Assistant Chat Endpoint
app.post('/api/assistant/chat', async (req, res) => {
  try {
    const { message, history, contextFacts } = req.body;
    if (!message || typeof message !== 'string') {
      res.status(400).json({ error: 'Message is required' });
      return;
    }

    // If Gemini is available, utilize gemini-3.8-flash with strict grounding
    if (ai) {
      try {
        const systemPrompt = `Bạn là Trợ lý AI Kho Bếp chuyên nghiệp và trung thực.
QUY TẮC BẮT BUỘC (GROUNDING TỐI THƯỢNG):
1. Bạn CHỈ ĐƯỢC PHÉP dùng số liệu từ DỮ LIỆU THỰC TẾ ĐƯỢC CUNG CẤP bên dưới.
2. TUYỆT ĐỐI KHÔNG tự bịa đặt, suy đoán số lượng tồn kho, doanh thu hoặc chi phí.
3. Nếu dữ liệu không được đề cập hoặc chưa đủ ngày theo dõi, BẮT BUỘC phải nói rõ là "chưa đủ cơ sở dữ liệu để kết luận".
4. Phân biệt rõ:
   - Dữ liệu thực tế (VERIFIED_FACT): Lô hàng đang có, đã bỏ, đã bán.
   - Dữ liệu ước tính (ESTIMATE): Đề xuất bổ sung hàng D25, biên lãi ước tính.
5. Luôn trả lời bằng tiếng Việt thân thiện, súc tích, chuyên nghiệp cho người làm bếp/quản lý nhà hàng.

DỮ LIỆU THỰC TẾ KHO HIỆN TẠI:
${JSON.stringify(contextFacts || {}, null, 2)}
`;

        const response = await ai.models.generateContent({
          model: 'gemini-3.8-flash',
          contents: `Câu hỏi của người quản lý kho: "${message}"`,
          config: {
            systemInstruction: systemPrompt,
          },
        });

        const generatedText = response.text || '';
        res.json({
          answer_text: generatedText,
          provider: 'external',
        });
        return;
      } catch (geminiError: unknown) {
        console.error('Gemini call error:', geminiError);
        // Fall through to server-fallback
      }
    }

    // Default server response indicator if no LLM
    res.json({
      answer_text: '',
      provider: 'rule_based',
    });
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : String(err);
    res.status(500).json({ error: errMsg });
  }
});

async function startServer() {
  const isProd = process.env.NODE_ENV === 'production';

  if (!isProd) {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static('dist'));
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server listening on http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error('Failed to start server:', err);
});
