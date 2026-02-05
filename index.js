/**
 * =============================================
 * BOT WHATSAPP DA ALMA - BAILEYS
 * =============================================
 * Download de audio funciona perfeitamente!
 * =============================================
 */

const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
    downloadMediaMessage,
    fetchLatestBaileysVersion
} = require('@whiskeysockets/baileys');
const pino = require('pino');
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const { exec } = require('child_process');
const { promisify } = require('util');
const execAsync = promisify(exec);
const qrcode = require('qrcode-terminal');

// Logger silencioso
const logger = pino({ level: 'silent' });

// =============================================
// CONFIGURACOES
// =============================================

const CONFIG = {
    openRouterApiKey: '',
    openRouterModel: 'openai/gpt-4o-mini',
    downloadsDir: path.join(__dirname, 'downloads'),
    audiosDir: path.join(__dirname, 'audios'),
    arquivosDir: path.join(__dirname, 'arquivos'),
    sessionDir: path.join(__dirname, 'auth_session'),
    nomeBot: 'Alma',
    ignorarGrupos: true,
    gruposPermitidos: [],
    voz: 'pt-BR-ThalitaMultilingualNeural',
    modeloWhisper: 'large',
    usarGPU: true
};

// Carrega config_bot.json se existir
const CONFIG_BOT_FILE = path.join(__dirname, 'config_bot.json');
if (fs.existsSync(CONFIG_BOT_FILE)) {
    try {
        const configBot = JSON.parse(fs.readFileSync(CONFIG_BOT_FILE, 'utf-8'));
        Object.assign(CONFIG, configBot);
        console.log('[CONFIG] Carregou config_bot.json');
    } catch (err) {
        console.error('[CONFIG] Erro ao carregar config_bot.json:', err.message);
    }
}

// Cria pastas necessarias
[CONFIG.downloadsDir, CONFIG.audiosDir, CONFIG.arquivosDir, CONFIG.sessionDir].forEach(dir => {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
});

// =============================================
// CARREGA CONFIGURACOES DO BOT PYTHON
// =============================================

let iaConfig = {};
let gatilhos = {};
let promptSistema = '';

function carregarConfiguracoes() {
    try {
        // Carrega ia_config.json da pasta atual
        const iaConfigPath = path.join(__dirname, 'ia_config.json');
        if (fs.existsSync(iaConfigPath)) {
            iaConfig = JSON.parse(fs.readFileSync(iaConfigPath, 'utf-8'));
            // Prioridade: variavel de ambiente > arquivo de config
            CONFIG.openRouterApiKey = process.env.OPENROUTER_API_KEY || iaConfig.api_key || '';
            CONFIG.openRouterModel = iaConfig.modelo || 'openai/gpt-4o-mini';
            promptSistema = iaConfig.prompt_sistema || '';
            console.log('[CONFIG] Carregou ia_config.json');
            console.log(`[CONFIG] API Key: ${CONFIG.openRouterApiKey ? 'Configurada' : 'NAO CONFIGURADA'}`);
            console.log(`[CONFIG] Prompt: ${promptSistema.substring(0, 50)}...`);
        } else {
            // Se nao tem arquivo, tenta variavel de ambiente
            CONFIG.openRouterApiKey = process.env.OPENROUTER_API_KEY || '';
            console.log('[AVISO] ia_config.json nao encontrado!');
            console.log(`[CONFIG] API Key (env): ${CONFIG.openRouterApiKey ? 'Configurada' : 'NAO CONFIGURADA'}`);
        }

        // Carrega gatilhos da pasta atual
        const gatilhosPath = path.join(__dirname, 'gatilhos_arquivos.json');
        if (fs.existsSync(gatilhosPath)) {
            gatilhos = JSON.parse(fs.readFileSync(gatilhosPath, 'utf-8'));
            console.log(`[CONFIG] Carregou ${Object.keys(gatilhos).length} gatilhos`);
        } else {
            console.log('[AVISO] gatilhos_arquivos.json nao encontrado!');
        }
    } catch (err) {
        console.error('[ERRO] Ao carregar configuracoes:', err.message);
    }
}

// =============================================
// HISTORICO DE CONVERSAS (PERSISTENTE)
// =============================================

const HISTORICO_FILE = path.join(__dirname, 'historico_conversas.json');
let historicoConversas = new Map();

// Carrega historico do arquivo ao iniciar
function carregarHistorico() {
    try {
        if (fs.existsSync(HISTORICO_FILE)) {
            const dados = JSON.parse(fs.readFileSync(HISTORICO_FILE, 'utf-8'));
            historicoConversas = new Map(Object.entries(dados));
            console.log(`[HISTORICO] Carregou conversas de ${historicoConversas.size} contatos`);
        }
    } catch (err) {
        console.error('[HISTORICO] Erro ao carregar:', err.message);
    }
}

// Salva historico no arquivo
function salvarHistorico() {
    try {
        const dados = Object.fromEntries(historicoConversas);
        fs.writeFileSync(HISTORICO_FILE, JSON.stringify(dados, null, 2), 'utf-8');
    } catch (err) {
        console.error('[HISTORICO] Erro ao salvar:', err.message);
    }
}

function obterHistorico(numero) {
    if (!historicoConversas.has(numero)) {
        historicoConversas.set(numero, []);
    }
    return historicoConversas.get(numero);
}

function adicionarAoHistorico(numero, role, content) {
    const historico = obterHistorico(numero);
    historico.push({ role, content, timestamp: Date.now() });

    // Mantém últimas 50 mensagens
    if (historico.length > 50) {
        historico.shift();
    }

    // Salva no arquivo a cada mensagem
    salvarHistorico();
}

// =============================================
// IA - OPENROUTER
// =============================================

async function consultarIA(numero, mensagem) {
    if (!CONFIG.openRouterApiKey) {
        console.log('[IA] API key nao configurada');
        return null;
    }

    try {
        const historico = obterHistorico(numero);
        const messages = [
            { role: 'system', content: promptSistema || 'Voce e Alma, uma coach emocional.' },
            ...historico,
            { role: 'user', content: mensagem }
        ];

        const response = await axios.post('https://openrouter.ai/api/v1/chat/completions', {
            model: CONFIG.openRouterModel,
            messages: messages,
            max_tokens: 500,
            temperature: 0.8
        }, {
            headers: {
                'Authorization': `Bearer ${CONFIG.openRouterApiKey}`,
                'Content-Type': 'application/json'
            }
        });

        const resposta = response.data.choices[0].message.content;
        adicionarAoHistorico(numero, 'user', mensagem);
        adicionarAoHistorico(numero, 'assistant', resposta);
        return resposta;

    } catch (err) {
        console.error('[IA] Erro:', err.message);
        return null;
    }
}

// =============================================
// GERAR AUDIO COM EDGE TTS
// =============================================

function detectarIdioma(texto) {
    // Palavras comuns para detectar idioma
    const portugues = ['você', 'voce', 'vc', 'tá', 'tô', 'né', 'pra', 'obrigado', 'obrigada', 'bom dia', 'boa tarde', 'boa noite', 'como', 'que', 'isso', 'isso', 'aqui', 'muito', 'também', 'mas', 'não', 'sim', 'quero', 'preciso', 'ajuda', 'por favor', 'brigada', 'brigado'];
    const espanhol = ['estás', 'estoy', 'qué', 'cómo', 'hola', 'gracias', 'buenos días', 'buenas tardes', 'buenas noches', 'quiero', 'necesito', 'ayuda', 'por favor', 'también', 'pero', 'aquí', 'mucho', 'muy'];
    const ingles = ['you', 'are', 'how', 'what', 'hello', 'hi', 'thanks', 'thank you', 'good morning', 'good afternoon', 'good night', 'want', 'need', 'help', 'please', 'also', 'but', 'here', 'very', 'much', 'the', 'is', 'are'];

    const textoLower = texto.toLowerCase();

    let scorePT = 0, scoreES = 0, scoreEN = 0;

    for (const palavra of portugues) {
        if (textoLower.includes(palavra)) scorePT++;
    }
    for (const palavra of espanhol) {
        if (textoLower.includes(palavra)) scoreES++;
    }
    for (const palavra of ingles) {
        if (textoLower.includes(palavra)) scoreEN++;
    }

    // Retorna o idioma com maior score
    if (scorePT >= scoreES && scorePT >= scoreEN) return 'pt';
    if (scoreES >= scorePT && scoreES >= scoreEN) return 'es';
    return 'en';
}

async function gerarAudioTTS(texto, idioma) {
    try {
        console.log(`[TTS] Gerando audio em ${idioma}...`);

        // Voz configuravel via config_bot.json
        const voz = CONFIG.voz || 'pt-BR-ThalitaMultilingualNeural';
        const nomeArquivo = `resposta_${Date.now()}.mp3`;
        const caminhoArquivo = path.join(CONFIG.downloadsDir, nomeArquivo);

        // Escapa aspas no texto
        const textoEscapado = texto.replace(/"/g, '\\"');

        const comando = `edge-tts --voice "${voz}" --text "${textoEscapado}" --write-media "${caminhoArquivo}"`;
        await execAsync(comando);

        if (fs.existsSync(caminhoArquivo)) {
            console.log(`[TTS] Audio gerado: ${caminhoArquivo}`);
            return caminhoArquivo;
        }

        return null;

    } catch (err) {
        console.error('[TTS] Erro ao gerar audio:', err.message);
        return null;
    }
}

// =============================================
// DOWNLOAD E TRANSCRICAO DE AUDIO
// =============================================

async function baixarAudio(message) {
    try {
        console.log('[AUDIO] Baixando audio...');

        // AQUI ESTA A MAGIA! Uma linha para baixar o audio!
        const buffer = await downloadMediaMessage(message, 'buffer', {});

        const nomeArquivo = `audio_${Date.now()}.ogg`;
        const caminhoArquivo = path.join(CONFIG.downloadsDir, nomeArquivo);

        fs.writeFileSync(caminhoArquivo, buffer);
        console.log(`[AUDIO] Audio salvo: ${caminhoArquivo}`);

        return caminhoArquivo;

    } catch (err) {
        console.error('[AUDIO] Erro ao baixar:', err.message);
        return null;
    }
}

async function transcreverAudio(caminhoAudio) {
    try {
        console.log('[WHISPER] Transcrevendo audio...');

        // Modelo e GPU configuraveis via config_bot.json
        const modelo = CONFIG.modeloWhisper || 'large';
        const device = CONFIG.usarGPU ? 'cuda' : 'cpu';
        const comando = `whisper "${caminhoAudio}" --model ${modelo} --device ${device} --output_format txt --output_dir "${CONFIG.downloadsDir}"`;
        await execAsync(comando);

        const txtPath = caminhoAudio.replace('.ogg', '.txt');
        if (fs.existsSync(txtPath)) {
            const transcricao = fs.readFileSync(txtPath, 'utf-8').trim();
            console.log(`[WHISPER] Transcricao: ${transcricao}`);

            try {
                fs.unlinkSync(caminhoAudio);
                fs.unlinkSync(txtPath);
            } catch {}

            return transcricao;
        }

        return null;

    } catch (err) {
        console.error('[WHISPER] Erro:', err.message);
        return null;
    }
}

// =============================================
// VERIFICAR GATILHOS
// =============================================

function verificarGatilho(mensagem) {
    const msgUpper = mensagem.toUpperCase().trim();

    // Palavras que indicam PEDIDO (ativa gatilho)
    const palavrasPedido = ['QUERO', 'MANDA', 'ENVIA', 'ENVIE', 'PASSA', 'ME DA', 'ME DÁ', 'PRECISO', 'NECESITO', 'QUIERO', 'ENVIAME', 'MANDAME', 'PASAME'];

    // Palavras que indicam COMENTARIO (não ativa gatilho)
    const palavrasComentario = ['FIZ', 'LI', 'VI', 'RECEBI', 'JA TENHO', 'YA TENGO', 'YA LEI', 'YA LO LEI', 'HICE', 'LEI O', 'LEI EL', 'SOBRE O', 'SOBRE EL', 'DO CHECKLIST', 'DEL CHECKLIST'];

    for (const [nome, config] of Object.entries(gatilhos)) {
        if (!config.ativo) continue;

        const nomeUpper = nome.toUpperCase();

        // Verifica se a mensagem contem a palavra-chave
        if (msgUpper.includes(nomeUpper)) {

            // CASO 1: Mensagem é SÓ a palavra-chave (ex: "checklist")
            if (msgUpper === nomeUpper) {
                return { nome, config };
            }

            // CASO 2: Mensagem COMEÇA com a palavra-chave (ex: "checklist por favor")
            if (msgUpper.startsWith(nomeUpper)) {
                return { nome, config };
            }

            // CASO 3: Tem palavra de PEDIDO antes (ex: "quero o checklist")
            for (const pedido of palavrasPedido) {
                if (msgUpper.includes(pedido)) {
                    return { nome, config };
                }
            }

            // CASO 4: Tem palavra de COMENTARIO? Não ativa gatilho, vai pra IA
            for (const comentario of palavrasComentario) {
                if (msgUpper.includes(comentario)) {
                    return null; // Vai pra IA
                }
            }

            // CASO 5: Mensagem curta (menos de 30 chars) com a palavra = provavelmente pedido
            if (msgUpper.length < 30) {
                return { nome, config };
            }
        }
    }
    return null;
}

// =============================================
// CONEXAO WHATSAPP
// =============================================

async function conectarWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState(CONFIG.sessionDir);

    const { version, isLatest } = await fetchLatestBaileysVersion();
    console.log(`[INFO] Usando WA v${version.join('.')}, isLatest: ${isLatest}`);

    // Detecta se esta rodando no Render (nuvem) ou local
    const isCloud = process.env.RENDER === 'true' || process.env.OPENROUTER_API_KEY;
    const phoneNumber = process.env.PHONE_NUMBER || ''; // Numero para pairing code

    const sock = makeWASocket({
        version,
        auth: state,
        logger,
        browser: ['Chrome', 'Windows', '10.0'],
        syncFullHistory: false,
        printQRInTerminal: !isCloud // So mostra QR se for local
    });

    // Se estiver na nuvem e tiver numero configurado, usa Pairing Code
    if (isCloud && phoneNumber && !state.creds.registered) {
        setTimeout(async () => {
            try {
                const code = await sock.requestPairingCode(phoneNumber);
                console.log('\n========================================');
                console.log('   CODIGO DE PAREAMENTO (PAIRING CODE)');
                console.log('========================================');
                console.log(`\n   SEU CODIGO: ${code}\n`);
                console.log('   Va no WhatsApp > Aparelhos conectados');
                console.log('   > Conectar aparelho > Conectar com numero');
                console.log('   > Digite o codigo acima');
                console.log('========================================\n');
            } catch (err) {
                console.log('[ERRO] Pairing code:', err.message);
            }
        }, 3000);
    }

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr && !isCloud) {
            console.log('\n========================================');
            console.log('   ESCANEIE O QR CODE NO TERMINAL');
            console.log('========================================\n');
            qrcode.generate(qr, { small: true });
        } else if (qr && isCloud) {
            console.log('[INFO] QR Code gerado - aguardando pairing code...');
        }

        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
            console.log(`[CONEXAO] Desconectado. Status: ${statusCode}`);
            if (shouldReconnect) {
                setTimeout(conectarWhatsApp, 5000);
            }
        } else if (connection === 'open') {
            console.log('\n[OK] BOT CONECTADO!\n');
        }
    });

    sock.ev.on('creds.update', saveCreds);

    // RECEBE MENSAGENS
    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return;

        for (const msg of messages) {
            await processarMensagem(sock, msg);
        }
    });

    // REJEITA LIGACOES
    sock.ev.on('call', async (calls) => {
        for (const call of calls) {
            if (call.status === 'offer') {
                console.log(`[LIGACAO] Rejeitando ligacao de ${call.from}`);
                await sock.rejectCall(call.id, call.from);
                await sock.sendMessage(call.from, {
                    text: 'Hola amor, en este momento no puedo atender llamadas, pero escribeme y te respondo con todo carino. Estoy aqui para ti.'
                });
            }
        }
    });

    return sock;
}

// =============================================
// PROCESSAR MENSAGENS
// =============================================

async function processarMensagem(sock, msg) {
    try {
        if (msg.key.fromMe) return;

        const isGroup = msg.key.remoteJid.endsWith('@g.us');

        // Verifica se é grupo
        if (isGroup) {
            // Se está na lista de grupos permitidos, responde
            if (CONFIG.gruposPermitidos.includes(msg.key.remoteJid)) {
                console.log(`[GRUPO PERMITIDO] ${msg.key.remoteJid}`);
            } else if (CONFIG.ignorarGrupos) {
                // Se não está na lista e ignorarGrupos está ativo, ignora
                return;
            }
        }

        // Ignora mensagens de broadcast/status
        if (msg.key.remoteJid === 'status@broadcast') return;

        const numero = msg.key.remoteJid;
        const nomeContato = msg.pushName || 'Desconhecido';

        console.log(`\n[MENSAGEM] De: ${nomeContato} (${numero})`);

        const messageContent = msg.message;
        if (!messageContent) return;

        let textoMensagem = '';
        let veioDeAudio = false; // NOVO: rastreia se a mensagem veio de audio

        // TEXTO
        if (messageContent.conversation) {
            textoMensagem = messageContent.conversation;
        } else if (messageContent.extendedTextMessage?.text) {
            textoMensagem = messageContent.extendedTextMessage.text;
        }

        // AUDIO - FUNCIONA PERFEITAMENTE!
        else if (messageContent.audioMessage) {
            console.log('[AUDIO] Recebeu mensagem de audio!');
            veioDeAudio = true; // NOVO: marca que veio de audio

            const caminhoAudio = await baixarAudio(msg);

            if (caminhoAudio) {
                const transcricao = await transcreverAudio(caminhoAudio);

                if (transcricao) {
                    textoMensagem = transcricao;
                    console.log(`[AUDIO] Transcricao: ${transcricao}`);
                } else {
                    await sock.sendMessage(numero, {
                        text: 'Disculpa amor, no pude entender tu audio. Me lo puedes escribir por favor?'
                    });
                    return;
                }
            } else {
                await sock.sendMessage(numero, {
                    text: 'Tuve un problema para escuchar tu audio. Puedes escribirme?'
                });
                return;
            }
        }

        if (!textoMensagem) {
            console.log('[MSG] Mensagem sem texto, ignorando');
            return;
        }

        console.log(`[MSG] Texto: ${textoMensagem.substring(0, 100)}...`);

        // 1. Verifica gatilhos
        const gatilho = verificarGatilho(textoMensagem);

        if (gatilho) {
            console.log(`[GATILHO] Ativou: ${gatilho.nome}`);

            // Envia APENAS o PDF, sem mensagem
            // Assim não sabemos o idioma ainda - o lead vai comentar e aí saberemos!
            if (gatilho.config.arquivos && gatilho.config.arquivos.length > 0) {
                for (const arquivo of gatilho.config.arquivos) {
                    const caminhoArquivo = path.join(__dirname, 'arquivos', arquivo);

                    if (fs.existsSync(caminhoArquivo)) {
                        await sock.sendMessage(numero, {
                            document: fs.readFileSync(caminhoArquivo),
                            fileName: arquivo,
                            mimetype: 'application/pdf'
                        });
                        console.log(`[ARQUIVO] Enviou: ${arquivo}`);
                    }
                }
            }
            return;
        }

        // 2. Consulta a IA
        // Mostra "digitando..." enquanto consulta a IA
        await sock.sendPresenceUpdate('composing', numero);

        const respostaIA = await consultarIA(numero, textoMensagem);

        if (respostaIA) {
            // NOVO: Se veio de audio, responde em audio!
            if (veioDeAudio) {
                // Mostra "gravando audio..." enquanto gera o TTS
                await sock.sendPresenceUpdate('recording', numero);

                const idioma = detectarIdioma(respostaIA);
                const audioPath = await gerarAudioTTS(respostaIA, idioma);

                // Delay de 10 segundos mostrando "gravando..." pra parecer humano
                console.log('[BOT] Aguardando 10s antes de enviar audio...');
                await new Promise(r => setTimeout(r, 10000));

                // Para de mostrar "gravando"
                await sock.sendPresenceUpdate('paused', numero);

                if (audioPath) {
                    // Envia como audio de voz (ptt = push to talk)
                    await sock.sendMessage(numero, {
                        audio: fs.readFileSync(audioPath),
                        mimetype: 'audio/mp4',
                        ptt: true // Isso faz aparecer como mensagem de voz
                    });
                    console.log(`[IA] Respondeu em AUDIO (${idioma}): ${respostaIA.substring(0, 100)}...`);

                    // Limpa o arquivo de audio
                    try { fs.unlinkSync(audioPath); } catch {}
                } else {
                    // Fallback: se falhar TTS, envia texto
                    await sock.sendMessage(numero, { text: respostaIA });
                    console.log(`[IA] Respondeu em TEXTO (TTS falhou): ${respostaIA.substring(0, 100)}...`);
                }
            } else {
                // Delay de 5 segundos mostrando "digitando..." pra parecer humano
                console.log('[BOT] Aguardando 5s antes de enviar texto...');
                await new Promise(r => setTimeout(r, 5000));

                // Para de mostrar "digitando"
                await sock.sendPresenceUpdate('paused', numero);

                // Mensagem de texto normal
                await sock.sendMessage(numero, { text: respostaIA });
                console.log(`[IA] Respondeu em TEXTO: ${respostaIA.substring(0, 100)}...`);
            }
        } else {
            await sock.sendPresenceUpdate('paused', numero);
            await sock.sendMessage(numero, {
                text: 'Perdon amor, tuve un problema. Puedes repetir?'
            });
        }

    } catch (err) {
        console.error('[ERRO] Ao processar mensagem:', err.message);
    }
}

// =============================================
// INICIALIZACAO
// =============================================

console.log('========================================');
console.log('BOT WHATSAPP DA ALMA - BAILEYS');
console.log('Download de audio funciona!');
console.log('========================================\n');

carregarConfiguracoes();
carregarHistorico();
conectarWhatsApp();
