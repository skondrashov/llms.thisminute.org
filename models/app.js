/* models/app.js - model catalog data + rendering.
 * Exposes window.__page for SPA router. */
(function () {
'use strict';
const MODELS = [
  // ─── Anthropic ────────────────────────────────────────
  { vendor: "Anthropic", name: "Claude Opus 4.7", ctx: "1M", tags: ["hosted", {label:"thinking",cls:"mint"}, {label:"vision",cls:"pink"}], summary: "Current Anthropic flagship. Substantially better at software engineering and vision than 4.6, with high-resolution image support up to 3.75MP.", url: "https://www.anthropic.com/claude" },
  { vendor: "Anthropic", name: "Claude Opus 4.6", ctx: "1M", tags: ["hosted", {label:"thinking",cls:"mint"}, {label:"vision",cls:"pink"}], summary: "Previous-generation flagship. Extended-thinking mode, 1M token window, image input. Superseded by Opus 4.7 but still widely deployed.", url: "https://www.anthropic.com/claude" },
  { vendor: "Anthropic", name: "Claude Sonnet 4.6", ctx: "1M", tags: ["hosted", {label:"thinking",cls:"mint"}, {label:"vision",cls:"pink"}], summary: "The workhorse. Most of Claude Code runs on this. Cheaper and faster than Opus, still extremely capable at long agentic work.", url: "https://www.anthropic.com/claude" },
  { vendor: "Anthropic", name: "Claude Haiku 4.5", ctx: "200K", tags: ["hosted", "fast", {label:"vision",cls:"pink"}], summary: "The small one. Built for speed and cheap bulk work. Great for triage and pre-filtering before handing off to a bigger model.", url: "https://www.anthropic.com/claude" },
  { vendor: "Anthropic", name: "Claude Sonnet 4.5", ctx: "1M", tags: ["hosted", {label:"thinking",cls:"mint"}, {label:"vision",cls:"pink"}], summary: "Previous workhorse generation. Still widely deployed in production. Excellent at long-running tool-use loops.", url: "https://www.anthropic.com/claude" },
  { vendor: "Anthropic", name: "Claude 3.7 Sonnet", ctx: "200K", tags: ["hosted", {label:"thinking",cls:"mint"}, {label:"vision",cls:"pink"}], summary: "First Claude with an extended-thinking mode. Bridged the gap between quick-response and reasoning models.", url: "https://www.anthropic.com/claude" },
  { vendor: "Anthropic", name: "Claude 3.5 Sonnet", ctx: "200K", tags: ["hosted", {label:"vision",cls:"pink"}], summary: "The one that kicked off serious agentic coding use. Lots of tools still pin to this version.", url: "https://www.anthropic.com/claude" },
  { vendor: "Anthropic", name: "Claude 3 Opus", ctx: "200K", tags: ["hosted", {label:"vision",cls:"pink"}], summary: "Original Claude 3 frontier. Strong at long creative writing. Still popular for specific analysis tasks.", url: "https://www.anthropic.com/claude" },

  // ─── OpenAI ────────────────────────────────────────
  { vendor: "OpenAI", name: "GPT-5.5", ctx: "1M", tags: ["hosted", {label:"thinking",cls:"mint"}, {label:"multimodal",cls:"pink"}], summary: "OpenAI's newest flagship. Stronger multi-step reasoning, agentic workflows, and coding. Matches GPT-5.4 latency at a much higher intelligence level.", url: "https://openai.com/index/introducing-gpt-5-5/" },
  { vendor: "OpenAI", name: "GPT-5", ctx: "256K", tags: ["hosted", {label:"thinking",cls:"mint"}, {label:"multimodal",cls:"pink"}], summary: "Original GPT-5 generation. Heavy multimodal support, built-in reasoning modes, and broad tool-calling. Superseded by GPT-5.5 but still widely used.", url: "https://openai.com/index/introducing-gpt-5/" },
  { vendor: "OpenAI", name: "GPT-5 Mini", ctx: "400K", tags: ["hosted", "fast", {label:"multimodal",cls:"pink"}], summary: "The smaller, cheaper GPT-5. Same shape, less horsepower. Solid default for API apps that don't need the full model.", url: "https://openai.com/api/" },
  { vendor: "OpenAI", name: "GPT-5 Nano", ctx: "400K", tags: ["hosted", "fast", "tiny"], summary: "The cheapest GPT-5 class. Built for extreme-scale bulk workloads where latency and cost dominate.", url: "https://openai.com/api/" },
  { vendor: "OpenAI", name: "o3", ctx: "200K", tags: ["hosted", {label:"thinking",cls:"mint"}], summary: "Dedicated reasoning model. Burns a lot of thinking tokens before answering, gets top marks on math and code benchmarks.", url: "https://openai.com/index/introducing-o3-and-o4-mini/" },
  { vendor: "OpenAI", name: "o4-mini", ctx: "200K", tags: ["hosted", {label:"thinking",cls:"mint"}, "fast"], summary: "Latest small reasoning model. Replaced o3-mini as the go-to for fast, cheap chain-of-thought work. Strong at math and code.", url: "https://openai.com/index/introducing-o3-and-o4-mini/" },
  { vendor: "OpenAI", name: "o3-mini", ctx: "128K", tags: ["hosted", {label:"thinking",cls:"mint"}, "fast"], summary: "Smaller reasoning model. Quick enough to drop into loops, strong on competitive math and programming tasks.", url: "https://openai.com/index/openai-o3-mini/" },
  { vendor: "OpenAI", name: "o1", ctx: "200K", tags: ["hosted", {label:"thinking",cls:"mint"}], summary: "The model that started the 'thinking out loud' generation of reasoning LLMs. Still in use, still expensive per query.", url: "https://openai.com/o1/" },
  { vendor: "OpenAI", name: "GPT-4.1", ctx: "1M", tags: ["hosted", {label:"coding",cls:"pink"}], summary: "Coding-focused model with a 1M token context window. Built for precise instruction following and large codebases. The go-to for API-driven code generation.", url: "https://openai.com/index/gpt-4-1/" },
  { vendor: "OpenAI", name: "GPT-4o", ctx: "128K", tags: ["hosted", {label:"multimodal",cls:"pink"}], summary: "Unified text / vision / audio model from 2024. Still the default for a lot of consumer-facing apps.", url: "https://openai.com/index/hello-gpt-4o/" },
  { vendor: "OpenAI", name: "GPT-4o Mini", ctx: "128K", tags: ["hosted", "fast", {label:"vision",cls:"pink"}], summary: "Cheap fast multimodal model. Replaced GPT-3.5 Turbo as the go-to cheap option in a lot of stacks.", url: "https://openai.com/api/" },
  { vendor: "OpenAI", name: "GPT-4 Turbo", ctx: "128K", tags: ["hosted", "legacy"], summary: "Pre-4o GPT-4 with a big context. Hangs around because a lot of older integrations pin to it.", url: "https://openai.com/api/" },
  { vendor: "OpenAI", name: "GPT-3.5 Turbo", ctx: "16K", tags: ["hosted", "legacy", "cheap"], summary: "The dirt-cheap original. Way past its prime but still alive as a fallback for ultra-simple tasks.", url: "https://openai.com/api/" },

  // ─── Google ────────────────────────────────────────
  { vendor: "Google", name: "Gemini 3.1 Pro", ctx: "1M", tags: ["hosted", {label:"thinking",cls:"mint"}, {label:"multimodal",cls:"pink"}], summary: "Google's current flagship. Outperforms Gemini 3 Pro on reasoning and multimodal benchmarks. Available via Gemini API, Vertex AI, and NotebookLM.", url: "https://deepmind.google/technologies/gemini/" },
  { vendor: "Google", name: "Gemini 3 Flash", ctx: "1M", tags: ["hosted", "fast", {label:"multimodal",cls:"pink"}], summary: "Gemini 3 Pro reasoning with Flash-line efficiency. Built for complex agentic workflows at lower cost and latency.", url: "https://deepmind.google/technologies/gemini/" },
  { vendor: "Google", name: "Gemini 3.1 Flash Lite", ctx: "1M", tags: ["hosted", "fast", "cheap"], summary: "Google's most cost-efficient Gemini 3 model. Multimodal input at $0.25/M input tokens. Built for high-volume translation, content moderation, and data extraction.", url: "https://deepmind.google/technologies/gemini/" },
  { vendor: "Google", name: "Gemini 2.5 Pro", ctx: "2M", tags: ["hosted", {label:"thinking",cls:"mint"}, {label:"video",cls:"pink"}], summary: "Biggest context window in the game at 2M tokens. Takes video as input natively. Google's bet on huge-context reasoning.", url: "https://deepmind.google/technologies/gemini/" },
  { vendor: "Google", name: "Gemini 2.5 Flash", ctx: "1M", tags: ["hosted", "fast", {label:"multimodal",cls:"pink"}], summary: "The fast, cheap Gemini. Still a huge 1M window, but prices itself to compete at the budget end.", url: "https://deepmind.google/technologies/gemini/" },
  { vendor: "Google", name: "Gemini 2.5 Flash Lite", ctx: "1M", tags: ["hosted", "fast", "cheap"], summary: "Even cheaper than Flash. Built for high-volume bulk workloads where you need multimodal but can't afford Pro.", url: "https://deepmind.google/technologies/gemini/" },
  { vendor: "Google", name: "Gemini 2.0 Pro", ctx: "1M", tags: ["hosted", {label:"multimodal",cls:"pink"}], summary: "Previous-generation frontier Gemini. Still deployed widely, especially in Workspace and Android integrations.", url: "https://deepmind.google/technologies/gemini/" },
  { vendor: "Google", name: "Gemini 2.0 Flash", ctx: "1M", tags: ["hosted", "fast", {label:"multimodal",cls:"pink"}], summary: "The 2.0 generation's speedster. Introduced native tool use and strong vision performance at low latency.", url: "https://deepmind.google/technologies/gemini/" },
  { vendor: "Google", name: "Gemini 1.5 Pro", ctx: "2M", tags: ["hosted", "legacy", {label:"multimodal",cls:"pink"}], summary: "The model that made 1M+ context windows normal. Still used where the very long context matters more than raw smarts.", url: "https://deepmind.google/technologies/gemini/" },
  { vendor: "Google", name: "Gemma 3 27B", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, "self-host"], summary: "Google's open-weights model built on Gemini research. Multilingual, vision-capable, and small enough to run on a single GPU.", url: "https://ai.google.dev/gemma" },
  { vendor: "Google", name: "Gemma 4 31B", ctx: "256K", tags: [{label:"open weights",cls:"mint"}, "self-host"], summary: "Google's most capable open model. 31B dense, multimodal, 140+ languages, Apache 2.0. Dominates math and competitive programming benchmarks for its size.", url: "https://ai.google.dev/gemma" },
  { vendor: "Google", name: "Gemma 4 26B MoE", ctx: "256K", tags: [{label:"open weights",cls:"mint"}, "MoE", "self-host"], summary: "MoE variant with only 3.8B active parameters. Runs on consumer GPUs while retaining strong performance. Apache 2.0.", url: "https://ai.google.dev/gemma" },
  { vendor: "Google", name: "Gemma 3 27B", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, "self-host"], summary: "Previous-gen open model built on Gemini research. Multilingual, vision-capable, and small enough to run on a single GPU.", url: "https://ai.google.dev/gemma" },
  { vendor: "Google", name: "Gemma 3 9B", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, "small", "self-host"], summary: "Smaller open Gemma. Runs on a laptop with enough VRAM. Popular for local dev and edge deployment.", url: "https://ai.google.dev/gemma" },

  // ─── Meta ────────────────────────────────────────
  { vendor: "Meta", name: "Llama 4 Behemoth", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, "frontier"], summary: "Meta's huge MoE flagship. Still unreleased as of mid-2026. Serves primarily as a teacher model for Scout and Maverick via codistillation.", url: "https://llama.meta.com/" },
  { vendor: "Meta", name: "Llama 4 Maverick", ctx: "1M", tags: [{label:"open weights",cls:"mint"}, "MoE", "self-host"], summary: "Mid-size MoE with a 1M token context window. The practical flagship for people self-hosting Llama 4. Strong coding and agentic performance.", url: "https://llama.meta.com/" },
  { vendor: "Meta", name: "Llama 4 Scout", ctx: "10M", tags: [{label:"open weights",cls:"mint"}, {label:"huge ctx",cls:"pink"}], summary: "Weird one. Tiny parameters but a 10M token context window thanks to a new attention scheme. For very-long-document workloads.", url: "https://llama.meta.com/" },
  { vendor: "Meta", name: "Llama 3.3 70B", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, "self-host"], summary: "Reliable open-weights workhorse. Most production self-hosted Llama deployments still run some variant of this.", url: "https://llama.meta.com/" },
  { vendor: "Meta", name: "Llama 3.2 Vision", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, {label:"vision",cls:"pink"}], summary: "First Llama with multimodal input. 11B and 90B flavors. Unlocked self-hosted vision for a lot of open-source projects.", url: "https://llama.meta.com/" },
  { vendor: "Meta", name: "Llama 3.1 405B", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, "huge"], summary: "Massive dense open-weights model. Proved that open models could hit frontier quality if you threw enough compute at them.", url: "https://llama.meta.com/" },

  // ─── Mistral ────────────────────────────────────────
  { vendor: "Mistral", name: "Mistral Large 3", ctx: "256K", tags: [{label:"open weights",cls:"mint"}, "MoE"], summary: "675B parameter open-weights MoE flagship. 41B active per token. Multimodal, multilingual, Apache 2.0. The largest open MoE from a major lab.", url: "https://mistral.ai/" },
  { vendor: "Mistral", name: "Mistral Small 4", ctx: "256K", tags: [{label:"open weights",cls:"mint"}, {label:"thinking",cls:"mint"}, {label:"vision",cls:"pink"}], summary: "119B MoE unifying reasoning, vision, and agentic coding. Only 6.5B active parameters. Configurable reasoning effort. Apache 2.0.", url: "https://mistral.ai/" },
  { vendor: "Mistral", name: "Mistral Large 2", ctx: "128K", tags: ["hosted", {label:"open weights",cls:"mint"}], summary: "Previous-generation French flagship. Weights released under research license, also available hosted. Superseded by Large 3.", url: "https://mistral.ai/" },
  { vendor: "Mistral", name: "Mistral Medium 3", ctx: "128K", tags: ["hosted"], summary: "The mid-range hosted model. Priced to compete with Sonnet and GPT-4o Mini for everyday production use.", url: "https://mistral.ai/" },
  { vendor: "Mistral", name: "Mistral Small 3", ctx: "32K", tags: [{label:"open weights",cls:"mint"}, "fast", "self-host"], summary: "Fully open small model. 24B parameters. Built to run fast on modest hardware.", url: "https://mistral.ai/" },
  { vendor: "Mistral", name: "Mistral Nemo", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, "small"], summary: "12B open-weights model built with NVIDIA. Tokenizer is notably efficient on non-English languages.", url: "https://mistral.ai/" },
  { vendor: "Mistral", name: "Mixtral 8x22B", ctx: "64K", tags: [{label:"open weights",cls:"mint"}, "MoE"], summary: "Open mixture-of-experts model. 8 experts, 22B each, only 2 active per token. Strong quality-per-inference-dollar.", url: "https://mistral.ai/" },
  { vendor: "Mistral", name: "Mixtral 8x7B", ctx: "32K", tags: [{label:"open weights",cls:"mint"}, "MoE", "small"], summary: "Original Mixtral. The model that made MoE mainstream in the open-weights world.", url: "https://mistral.ai/" },
  { vendor: "Mistral", name: "Codestral", ctx: "32K", tags: [{label:"open weights",cls:"mint"}, {label:"coding",cls:"pink"}], summary: "Mistral's specialized coding model. Trained on 80+ programming languages. Great for self-hosted code assistants.", url: "https://mistral.ai/" },

  // ─── DeepSeek ────────────────────────────────────────
  { vendor: "DeepSeek", name: "DeepSeek V4 Pro", ctx: "1M", tags: [{label:"open weights",cls:"mint"}, "MoE", "self-host"], summary: "Fourth-generation flagship. 1.6T parameters, 49B active. 1M context with only 27% of V3's inference FLOPs. MIT license.", url: "https://www.deepseek.com/" },
  { vendor: "DeepSeek", name: "DeepSeek V4 Flash", ctx: "1M", tags: [{label:"open weights",cls:"mint"}, "MoE", "fast"], summary: "284B parameter fast MoE. 13B active per token, 1M context. Built for high-throughput workloads at minimal cost. MIT license.", url: "https://www.deepseek.com/" },
  { vendor: "DeepSeek", name: "DeepSeek R1", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, {label:"thinking",cls:"mint"}, "self-host"], summary: "Open-weights reasoning model that shocked everyone by being nearly as good as frontier models on math and code for a fraction of the training cost.", url: "https://www.deepseek.com/" },
  { vendor: "DeepSeek", name: "DeepSeek V3", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, "MoE", "self-host"], summary: "The non-reasoning DeepSeek. Large MoE model, cheap to run, fast, general-purpose. Very popular as a self-hosted workhorse.", url: "https://www.deepseek.com/" },
  { vendor: "DeepSeek", name: "DeepSeek R1 Distill", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, "small"], summary: "Reasoning traces from R1 distilled into smaller base models (Llama, Qwen). Runs on consumer hardware, retains a lot of the reasoning behavior.", url: "https://www.deepseek.com/" },
  { vendor: "DeepSeek", name: "DeepSeek Coder V2", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, {label:"coding",cls:"pink"}], summary: "Coding-specialized DeepSeek. Strong at repo-scale completion and refactoring. Self-hostable for code assistants.", url: "https://www.deepseek.com/" },
  { vendor: "DeepSeek", name: "DeepSeek V2", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, "legacy"], summary: "Previous-generation V2. Still in use in self-hosted setups that haven't upgraded yet.", url: "https://www.deepseek.com/" },

  // ─── Alibaba (Qwen) ────────────────────────────────────────
  { vendor: "Alibaba", name: "Qwen 3.6", ctx: "256K", tags: [{label:"open weights",cls:"mint"}, "multilingual", {label:"coding",cls:"pink"}], summary: "Qwen's current flagship generation. 256K native context extensible to 1M tokens. Sizes from 2B to 35B. Excels at agentic coding and repository-level reasoning.", url: "https://qwenlm.github.io/" },
  { vendor: "Alibaba", name: "Qwen 2.5 72B", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, "self-host"], summary: "Previous-gen workhorse. Competitive with Llama 70B at the time, still widely deployed.", url: "https://qwenlm.github.io/" },
  { vendor: "Alibaba", name: "Qwen 2.5 Coder", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, {label:"coding",cls:"pink"}], summary: "Code-specialized Qwen. Trained on a huge multi-language code corpus. Powers a lot of open coding assistants.", url: "https://qwenlm.github.io/" },
  { vendor: "Alibaba", name: "Qwen 2 VL", ctx: "32K", tags: [{label:"open weights",cls:"mint"}, {label:"vision",cls:"pink"}], summary: "Vision-capable Qwen. Handles complex documents and charts. Popular for document-parsing pipelines you want to self-host.", url: "https://qwenlm.github.io/" },
  { vendor: "Alibaba", name: "Qwen Audio", ctx: "32K", tags: [{label:"open weights",cls:"mint"}, {label:"audio",cls:"pink"}], summary: "Audio-in, text-out. Transcription, audio understanding, music analysis. One of the few open audio-capable models.", url: "https://qwenlm.github.io/" },

  // ─── xAI ────────────────────────────────────────
  { vendor: "xAI", name: "Grok 4.3", ctx: "1M", tags: ["hosted", {label:"thinking",cls:"mint"}, {label:"video",cls:"pink"}], summary: "xAI's latest flagship. Native video input, 1M token context, aggressive pricing at $1.25/M input tokens.", url: "https://x.ai/" },
  { vendor: "xAI", name: "Grok 3", ctx: "128K", tags: ["hosted", {label:"thinking",cls:"mint"}, {label:"vision",cls:"pink"}], summary: "Previous xAI flagship. Superseded by Grok 4 series but still available via API and integrated into X.", url: "https://x.ai/" },
  { vendor: "xAI", name: "Grok 2", ctx: "128K", tags: ["hosted", "legacy"], summary: "The previous Grok generation. Vision support added late in its lifecycle. Still used in parts of the X ecosystem.", url: "https://x.ai/" },

  // ─── Cohere ────────────────────────────────────────
  { vendor: "Cohere", name: "Command A", ctx: "256K", tags: ["hosted", {label:"open weights",cls:"mint"}, "RAG"], summary: "Cohere's current flagship. 111B parameters, runs on just two GPUs, 150% throughput of Command R+. Excels at agentic, multilingual, and RAG workflows.", url: "https://cohere.com/command" },
  { vendor: "Cohere", name: "Command R+", ctx: "128K", tags: ["hosted", {label:"open weights",cls:"mint"}, "RAG"], summary: "Cohere's flagship, purpose-built for RAG and tool-use workflows. Weights released. Popular for enterprise search applications.", url: "https://cohere.com/command" },
  { vendor: "Cohere", name: "Command R", ctx: "128K", tags: ["hosted", {label:"open weights",cls:"mint"}, "RAG"], summary: "Smaller, cheaper Command. Same RAG-first design. Sweet spot for retrieval-heavy pipelines on a budget.", url: "https://cohere.com/command" },

  // ─── Microsoft ────────────────────────────────────────
  { vendor: "Microsoft", name: "Phi-4", ctx: "16K", tags: [{label:"open weights",cls:"mint"}, "small", "self-host"], summary: "14B parameter model that punches way above its weight on math and reasoning benchmarks. Trained on synthetic data, not internet scrape.", url: "https://azure.microsoft.com/en-us/products/phi" },
  { vendor: "Microsoft", name: "Phi-3 Medium", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, "small"], summary: "14B model with a long context. Designed to fit on smaller devices while still handling whole documents.", url: "https://azure.microsoft.com/en-us/products/phi" },
  { vendor: "Microsoft", name: "Phi-3 Mini", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, "tiny", "self-host"], summary: "3.8B parameters. Runs on a phone. Built to prove that carefully curated training data beats brute scale for small models.", url: "https://azure.microsoft.com/en-us/products/phi" },

  // ─── Others ────────────────────────────────────────
  { vendor: "Others", name: "NVIDIA Nemotron", ctx: "128K", tags: [{label:"open weights",cls:"mint"}, "self-host"], summary: "NVIDIA's own open-weights model family. Based on Llama with NVIDIA training tricks. Competitive with Llama 70B.", url: "https://huggingface.co/nvidia" },
  { vendor: "Others", name: "Databricks DBRX", ctx: "32K", tags: [{label:"open weights",cls:"mint"}, "MoE"], summary: "132B parameter MoE from Databricks. Released for people running LLMs on Databricks' platform, but the weights are open.", url: "https://www.databricks.com/blog/introducing-dbrx-new-state-art-open-llm" },
  { vendor: "Others", name: "Moonshot Kimi", ctx: "2M", tags: ["hosted", {label:"huge ctx",cls:"pink"}], summary: "Chinese AI startup. Famous for one of the earliest 2M-token context windows. Strong at long-document understanding.", url: "https://kimi.moonshot.cn/" },
  { vendor: "Others", name: "01.AI Yi Lightning", ctx: "128K", tags: ["hosted", "fast"], summary: "01.AI's latest. Fast, cheap, and surprisingly capable. Competitive with GPT-4o class models on benchmarks.", url: "https://01.ai/" },
  { vendor: "Others", name: "Baidu Ernie 4.5", ctx: "128K", tags: ["hosted"], summary: "Baidu's flagship. Dominant in the Chinese-language market and integrated throughout Baidu's products.", url: "https://ernie.baidu.com/" }
];

var U = CatalogUtils;
var grouped = U.groupBy(MODELS, 'vendor');
var groups = grouped.groups;
var order = grouped.order;

var activeFilter = null;

function renderCard(m) {
  var e = U.esc;
  return (
    '<a class="catalog-card" href="'+m.url+'" target="_blank" rel="noopener">'+
      '<div class="catalog-card-name">'+e(m.name)+'</div>'+
      '<div class="catalog-card-detail lg">'+
        '<span class="value">'+e(m.ctx)+'</span>'+
        '<span class="label">ctx</span>'+
      '</div>'+
      '<div class="catalog-tags">'+m.tags.map(U.tagHtml).join('')+'</div>'+
      '<div class="catalog-card-summary">'+e(m.summary)+'</div>'+
      '<div class="catalog-card-foot"><span class="out">read more &rarr;</span></div>'+
    '</a>'
  );
}

function renderNav() {
  var navEl = document.getElementById('catalog-nav');
  navEl.innerHTML = order.map(function(v) {
    var cls = activeFilter === v ? ' class="active"' : '';
    return '<button data-vendor="'+U.esc(v)+'"'+cls+'>'+U.esc(v)+'</button>';
  }).join('');

  navEl.querySelectorAll('button').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var vendor = btn.getAttribute('data-vendor');
      activeFilter = activeFilter === vendor ? null : vendor;
      renderNav();
      renderCatalog();
    });
  });
}

function renderCatalog() {
  var visibleVendors = activeFilter ? [activeFilter] : order;

  var html = visibleVendors.map(function(vendor) {
    var items = groups[vendor];
    var cards = items.map(renderCard).join('');
    return (
      '<section class="catalog-section" id="'+U.slug(vendor)+'">'+
        '<div class="catalog-section-head">'+
          '<span class="catalog-section-name">'+U.esc(vendor)+'</span>'+
          '<span class="catalog-section-count">'+items.length+' model'+(items.length !== 1 ? 's' : '')+'</span>'+
        '</div>'+
        '<div class="catalog-grid">'+cards+'</div>'+
      '</section>'
    );
  }).join('');
  document.getElementById('catalog-grid').innerHTML = html;
}

function init() {
  activeFilter = null;
  document.getElementById('catalog-stats').innerHTML =
    '<span><span class="stat-value">'+MODELS.length+'</span><span class="stat-label">models</span></span>'+
    '<span><span class="stat-value">'+order.length+'</span><span class="stat-label">vendors</span></span>';
  renderNav();
  renderCatalog();
  CatalogUtils.initBackToTop();
}

window.__page = { init: init, teardown: function() {} };
init();
})();
