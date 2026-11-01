/* AgroEstoque – interface integrada à API REST (/api/). JavaScript puro, sem dependências. */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const GESTAO = ['ADMINISTRADOR', 'GESTOR'];
  const MOTIVOS = {
    ENTRADA: [['COMPRA', 'Compra de fornecedor'], ['DEVOLUCAO_CLIENTE', 'Devolução de cliente'], ['AJUSTE_POSITIVO', 'Ajuste de inventário (+)']],
    SAIDA: [['VENDA', 'Venda'], ['PERDA', 'Perda ou avaria'], ['AJUSTE_NEGATIVO', 'Ajuste de inventário (-)'], ['DEVOLUCAO_FORNECEDOR', 'Devolução a fornecedor']],
  };
  const state = { token: sessionStorage.getItem('ae_token'), user: null, editId: null,
                  prodPage: 1, prodPages: 1, movPage: 1, movPages: 1, tipo: 'ENTRADA', produtos: [] };

  // ---------------------------------------------------------- utilitários
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const num = (v) => Number(v).toLocaleString('pt-BR');
  const money = (v) => Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const dt = (iso) => new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  const isGestao = () => state.user && GESTAO.includes(state.user.papel);
  const PAPEIS = { ADMINISTRADOR: 'Administrador', GESTOR: 'Gestor', OPERADOR: 'Operador' };

  let toastTimer;
  function toast(msg, erro = false) {
    const t = $('#toast');
    t.textContent = msg;
    t.className = 'toast show' + (erro ? ' error' : '');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.className = 'toast'; }, 3800);
  }
  function showError(sel, err) {
    const box = $(sel);
    let msg = err.message || 'Erro inesperado.';
    if (err.detalhes && Object.keys(err.detalhes).length) {
      const partes = Object.entries(err.detalhes).filter(([, v]) => Array.isArray(v))
        .map(([k, v]) => `${k === '__all__' ? '' : k + ': '}${v.join(' ')}`);
      if (partes.length) msg += ' ' + partes.join(' | ');
    }
    box.textContent = msg;
    box.classList.remove('hidden');
  }
  const hideError = (sel) => $(sel).classList.add('hidden');

  async function api(caminho, { method = 'GET', body } = {}) {
    const headers = { Accept: 'application/json' };
    if (state.token) headers.Authorization = 'Bearer ' + state.token;
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    let resp;
    try {
      resp = await fetch('/api/' + caminho, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
    } catch (e) {
      const err = new Error('Não foi possível conectar ao servidor.'); throw err;
    }
    let dados = null;
    try { dados = await resp.json(); } catch (e) { /* sem corpo */ }
    if (!resp.ok) {
      const e = (dados && dados.erro) || {};
      const err = new Error(e.mensagem || 'Erro ' + resp.status);
      err.status = resp.status; err.codigo = e.codigo; err.detalhes = e.detalhes;
      if (resp.status === 401 && caminho !== 'auth/login') { sair('Sua sessão expirou. Entre novamente.'); }
      throw err;
    }
    return dados;
  }

  // ------------------------------------------------------- login / sessão
  function entrarNoApp(usuario) {
    state.user = usuario;
    $('#login').classList.add('hidden');
    $('#app').classList.remove('hidden');
    $('#userName').textContent = usuario.nome;
    $('#userRole').textContent = PAPEIS[usuario.papel] || usuario.papel;
    $('#shopUser').textContent = usuario.email || usuario.username;
    $('#newProduct').classList.toggle('hidden', !isGestao());
    $('#genRecs').classList.toggle('hidden', !isGestao());
    $('#navUsuarios').classList.toggle('hidden', usuario.papel !== 'ADMINISTRADOR');
    abrir('dashboard');
  }
  function sair(msg) {
    state.token = null; state.user = null; state.editId = null;
    state.prodPage = 1; state.movPage = 1; state.produtos = [];
    sessionStorage.removeItem('ae_token');
    // limpa tudo o que foi renderizado para que a próxima pessoa não veja dados da sessão anterior
    ['#recs', '#productRows', '#movList', '#userRows', '#acaoList', '#topList', '#chart7',
     '#mProduto', '#listaCategorias', '#mSaldo'].forEach((sel) => { $(sel).innerHTML = ''; });
    ['#productForm'].forEach((sel) => $(sel).classList.add('hidden'));
    ['#stProdutos', '#stCategorias', '#stBaixo', '#stCriticos', '#stVendas', '#stVariacao', '#stFat']
      .forEach((sel) => { $(sel).textContent = '—'; });
    $('#recBadge').classList.add('hidden');
    $('#app').classList.add('hidden');
    $('#login').classList.remove('hidden');
    $('#loginSenha').value = '';
    if (msg) { $('#loginError').textContent = msg; $('#loginError').classList.remove('hidden'); }
  }
  $('#loginForm').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    hideError('#loginError');
    const btn = $('#enter'); btn.disabled = true;
    try {
      const r = await api('auth/login', { method: 'POST', body: { email: $('#loginEmail').value, senha: $('#loginSenha').value } });
      state.token = r.token; sessionStorage.setItem('ae_token', r.token);
      entrarNoApp(r.usuario);
    } catch (e) { showError('#loginError', e); } finally { btn.disabled = false; }
  });
  $('#logout').addEventListener('click', () => sair());

  // ------------------------------------------------------------ navegação
  const TITULOS = { dashboard: 'Visão geral', produtos: 'Produtos', movimentacoes: 'Movimentações', recomendacoes: 'Recomendações', usuarios: 'Usuários' };
  function abrir(view) {
    $$('.page').forEach((p) => p.classList.toggle('active', p.id === view));
    $$('.nav button').forEach((b) => b.classList.toggle('active', b.dataset.view === view));
    $('#viewTitle').textContent = TITULOS[view];
    $('#sidebar').classList.remove('open'); $('#overlay').classList.remove('open');
    const carregar = { dashboard: carregarDashboard, produtos: carregarProdutos, movimentacoes: carregarMovimentacoes, recomendacoes: carregarRecomendacoes, usuarios: carregarUsuarios }[view];
    carregar().catch((e) => toast(e.message, true));
    atualizarBadge();
  }
  $$('.nav button').forEach((b) => b.addEventListener('click', () => abrir(b.dataset.view)));
  $('#mobileMenu').addEventListener('click', () => { $('#sidebar').classList.toggle('open'); $('#overlay').classList.toggle('open'); });
  $('#overlay').addEventListener('click', () => { $('#sidebar').classList.remove('open'); $('#overlay').classList.remove('open'); });

  async function atualizarBadge() {
    try {
      const r = await api('recomendacoes?status=PENDENTE');
      const b = $('#recBadge'); b.textContent = r.total; b.classList.toggle('hidden', r.total === 0);
    } catch (e) { /* ignora */ }
  }

  // ------------------------------------------------------------ dashboard
  async function carregarDashboard() {
    const d = await api('dashboard');
    const data = new Date(d.data_referencia + 'T12:00:00');
    $('#dashDate').textContent = data.toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' }).toUpperCase();
    const hora = new Date().getHours();
    $('#dashGreeting').textContent = (hora < 12 ? 'Bom dia' : hora < 18 ? 'Boa tarde' : 'Boa noite') + '! Veja o que precisa de atenção.';
    $('#stProdutos').textContent = num(d.total_produtos);
    $('#stCategorias').textContent = `${d.total_categorias} categorias`;
    $('#stBaixo').textContent = num(d.estoque_baixo);
    $('#stCriticos').textContent = `${d.itens_criticos} itens críticos`;
    $('#stVendas').textContent = num(d.vendas_mes_unidades);
    $('#stVariacao').textContent = d.variacao_vendas_percentual === null ? 'sem base de comparação'
      : `${d.variacao_vendas_percentual > 0 ? '+' : ''}${String(d.variacao_vendas_percentual).replace('.', ',')}% vs. mês anterior`;
    $('#stFat').textContent = money(d.faturamento_mes);

    const max = Math.max(1, ...d.saidas_ultimos_7_dias.map((x) => x.quantidade));
    $('#chart7').innerHTML = d.saidas_ultimos_7_dias.map((x) =>
      `<div class="bar" style="height:${Math.max(3, Math.round(x.quantidade / max * 100))}%"><b>${x.quantidade}</b><span>${esc(x.rotulo)}</span></div>`).join('');

    $('#acaoList').innerHTML = d.produtos_exigem_acao.length ? d.produtos_exigem_acao.map((a) =>
      `<div class="alert-row"><span class="dot ${a.nivel === 'CRITICO' ? 'red' : 'amber'}"></span><div><b>${esc(a.produto)}</b><small>${num(a.saldo)} unidade(s) disponíveis</small></div>›</div>`).join('')
      : '<div class="empty">Nenhum produto exige ação no momento. ✔</div>';
    $('#topList').innerHTML = d.produtos_mais_vendidos.length ? d.produtos_mais_vendidos.map((p, i) =>
      `<div class="movement"><span class="avatar">${i + 1}</span><div><b>${esc(p.produto)}</b></div><strong>${num(p.quantidade)} un.</strong></div>`).join('')
      : '<div class="empty">Ainda não há vendas registradas.</div>';
  }

  // -------------------------------------------------------------- produtos
  const BADGE = { CRITICO: ['badge-red', 'Crítico'], ATENCAO: ['badge-amber', 'Atenção'], NORMAL: ['badge-green', 'Normal'] };
  async function carregarProdutos() {
    const q = $('#search').value.trim(), sit = $('#fSituacao').value;
    const qs = new URLSearchParams({ page: state.prodPage, page_size: 15 });
    if (q) qs.set('q', q); if (sit) qs.set('situacao', sit);
    const r = await api('produtos?' + qs);
    state.prodPages = r.paginas;
    $('#count').textContent = `${num(r.total)} item(ns)`;
    $('#prodPageInfo').textContent = `Página ${r.pagina} de ${r.paginas}`;
    $('#prodPrev').disabled = r.pagina <= 1; $('#prodNext').disabled = r.pagina >= r.paginas;
    $('#productRows').innerHTML = r.resultados.length ? r.resultados.map((p) => {
      const [cls, rot] = BADGE[p.situacao];
      const acoes = isGestao() ? `<div class="row-actions"><button class="btn btn-outline btn-sm" data-edit="${p.id}">Editar</button><button class="btn btn-danger btn-sm" data-del="${p.id}">Desativar</button></div>` : '';
      return `<tr><td>${esc(p.nome)}<br><small style="color:#999">${esc(p.sku)}</small></td><td>${esc(p.categoria)}</td><td>${money(p.preco_venda)}</td><td>${num(p.quantidade_atual)}</td><td>${num(p.estoque_minimo)}</td><td><span class="badge ${cls}">${rot}</span></td><td>${acoes}</td></tr>`;
    }).join('') : '<tr><td colspan="7" class="empty">Nenhum produto encontrado.</td></tr>';
    const cats = await api('categorias');
    $('#listaCategorias').innerHTML = cats.map((c) => `<option value="${esc(c.nome)}">`).join('');
  }
  let buscaTimer;
  $('#search').addEventListener('input', () => { clearTimeout(buscaTimer); buscaTimer = setTimeout(() => { state.prodPage = 1; carregarProdutos().catch((e) => toast(e.message, true)); }, 300); });
  $('#fSituacao').addEventListener('change', () => { state.prodPage = 1; carregarProdutos().catch((e) => toast(e.message, true)); });
  $('#prodPrev').addEventListener('click', () => { state.prodPage = Math.max(1, state.prodPage - 1); carregarProdutos(); });
  $('#prodNext').addEventListener('click', () => { state.prodPage = Math.min(state.prodPages, state.prodPage + 1); carregarProdutos(); });

  async function carregarFornecedores() {
    const f = await api('fornecedores');
    $('#pForn').innerHTML = '<option value="">— nenhum —</option>' + f.filter((x) => x.ativo)
      .map((x) => `<option value="${x.id}">${esc(x.nome)} (${x.prazo_entrega_dias} dias)</option>`).join('');
  }
  function abrirForm(produto) {
    state.editId = produto ? produto.id : null;
    $('#formTitle').textContent = produto ? 'Editar produto' : 'Cadastrar novo produto';
    $('#saveProduct').textContent = produto ? 'Salvar alterações' : 'Salvar produto';
    $('#pQtdWrap').classList.toggle('hidden', !!produto);
    $('#pNome').value = produto ? produto.nome : ''; $('#pCategoria').value = produto ? produto.categoria : '';
    $('#pSku').value = produto ? produto.sku : ''; $('#pUnidade').value = produto ? produto.unidade : 'unidade';
    $('#pPreco').value = produto ? String(produto.preco_venda).replace('.', ',') : '';
    $('#pQtd').value = 0; $('#pMin').value = produto ? produto.estoque_minimo : 0;
    carregarFornecedores().then(() => { $('#pForn').value = produto && produto.fornecedor_id ? produto.fornecedor_id : ''; });
    hideError('#productError');
    $('#productForm').classList.remove('hidden');
    $('#productForm').scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  $('#newProduct').addEventListener('click', () => abrirForm(null));
  $('#cancelProduct').addEventListener('click', () => $('#productForm').classList.add('hidden'));
  $('#saveProduct').addEventListener('click', async () => {
    hideError('#productError');
    const corpo = { nome: $('#pNome').value, categoria: $('#pCategoria').value, unidade: $('#pUnidade').value,
      preco_venda: $('#pPreco').value, estoque_minimo: $('#pMin').value || 0,
      fornecedor_id: $('#pForn').value || null };
    if ($('#pSku').value.trim()) corpo.sku = $('#pSku').value;
    if (!state.editId) corpo.quantidade_atual = $('#pQtd').value || 0;
    const btn = $('#saveProduct'); btn.disabled = true;
    try {
      await api(state.editId ? `produtos/${state.editId}` : 'produtos', { method: state.editId ? 'PATCH' : 'POST', body: corpo });
      toast(state.editId ? 'Produto atualizado.' : 'Produto cadastrado com sucesso.');
      $('#productForm').classList.add('hidden');
      await carregarProdutos(); atualizarBadge();
    } catch (e) { showError('#productError', e); } finally { btn.disabled = false; }
  });
  $('#productRows').addEventListener('click', async (ev) => {
    const ed = ev.target.closest('[data-edit]'), del = ev.target.closest('[data-del]');
    try {
      if (ed) abrirForm(await api('produtos/' + ed.dataset.edit));
      if (del && confirm('Desativar este produto? O histórico de movimentações será mantido.')) {
        await api('produtos/' + del.dataset.del, { method: 'DELETE' });
        toast('Produto desativado.'); await carregarProdutos(); atualizarBadge();
      }
    } catch (e) { toast(e.message, true); }
  });

  // --------------------------------------------------------- movimentações
  function montarMotivos() {
    $('#mMotivo').innerHTML = MOTIVOS[state.tipo].map(([v, r]) => `<option value="${v}">${r}</option>`).join('');
  }
  function mostrarSaldo() {
    const p = state.produtos.find((x) => String(x.id) === $('#mProduto').value);
    $('#mSaldo').textContent = p ? `Saldo atual: ${num(p.quantidade_atual)} ${p.unidade}(s)` : '';
  }
  async function carregarMovimentacoes() {
    montarMotivos();
    const [prods, movs] = await Promise.all([api('produtos?page_size=100'), api(`movimentacoes?page=${state.movPage}&page_size=8`)]);
    state.produtos = prods.resultados;
    const atual = $('#mProduto').value;
    $('#mProduto').innerHTML = prods.resultados.map((p) => `<option value="${p.id}">${esc(p.nome)}</option>`).join('');
    if (atual) $('#mProduto').value = atual;
    mostrarSaldo();
    state.movPages = movs.paginas;
    $('#movPageInfo').textContent = `Página ${movs.pagina} de ${movs.paginas}`;
    $('#movPrev').disabled = movs.pagina <= 1; $('#movNext').disabled = movs.pagina >= movs.paginas;
    $('#movList').innerHTML = movs.resultados.length ? movs.resultados.map((m) =>
      `<div class="movement"><span class="avatar">${m.tipo === 'ENTRADA' ? '↓' : '↑'}</span><div><b>${esc(m.produto)}</b><small>${dt(m.data)} • ${esc(m.motivo_descricao)}${m.usuario ? ' • ' + esc(m.usuario) : ''}</small></div><strong>${m.tipo === 'ENTRADA' ? '+' : '-'} ${num(m.quantidade)} un.</strong></div>`).join('')
      : '<div class="empty">Nenhuma movimentação registrada.</div>';
  }
  $$('.type').forEach((b) => b.addEventListener('click', () => {
    state.tipo = b.dataset.type;
    $$('.type').forEach((x) => x.classList.toggle('selected', x === b));
    montarMotivos();
  }));
  $('#mProduto').addEventListener('change', mostrarSaldo);
  $('#movPrev').addEventListener('click', () => { state.movPage = Math.max(1, state.movPage - 1); carregarMovimentacoes(); });
  $('#movNext').addEventListener('click', () => { state.movPage = Math.min(state.movPages, state.movPage + 1); carregarMovimentacoes(); });
  $('#saveMovement').addEventListener('click', async () => {
    hideError('#movError');
    const btn = $('#saveMovement'); btn.disabled = true;
    try {
      const m = await api('movimentacoes', { method: 'POST', body: {
        produto_id: Number($('#mProduto').value), tipo: state.tipo, motivo: $('#mMotivo').value,
        quantidade: $('#mQtd').value, observacao: $('#mObs').value } });
      toast(`Movimentação registrada. Novo saldo: ${num(m.saldo_apos)}.`);
      $('#mQtd').value = 1; $('#mObs').value = ''; state.movPage = 1;
      await carregarMovimentacoes(); atualizarBadge();
    } catch (e) { showError('#movError', e); } finally { btn.disabled = false; }
  });

  // -------------------------------------------------------- recomendações
  async function carregarRecomendacoes() {
    const r = await api('recomendacoes?status=PENDENTE');
    const b = $('#recBadge'); b.textContent = r.total; b.classList.toggle('hidden', r.total === 0);
    $('#recs').innerHTML = r.resultados.length ? r.resultados.map((x) => {
      const crit = x.nivel === 'CRITICO';
      const decisao = isGestao() ? `<button class="btn btn-primary btn-sm" data-dec="ACEITA" data-id="${x.id}">✓ Aceitar sugestão</button><button class="btn btn-outline btn-sm" data-dec="IGNORADA" data-id="${x.id}">Ignorar</button>` : '';
      return `<div class="card rec" id="rec-${x.id}"><span class="rec-icon" ${crit ? '' : 'style="background:#fff0cc;color:#8a5b00"'}>⚠</span>
        <div><h3>${esc(x.produto)} <span class="badge ${crit ? 'badge-red' : 'badge-amber'}">${esc(x.nivel_descricao)}</span></h3><p>${esc(x.justificativa)}</p><strong>✦ ${esc(x.acao_sugerida)}</strong></div>
        <div class="rec-actions">${decisao}<button class="btn btn-outline btn-sm" data-analise="${x.produto_id}" data-id="${x.id}">Analisar produto</button></div>
        <div class="rec-detail" id="det-${x.id}"></div></div>`;
    }).join('') : '<div class="card empty">Nenhuma recomendação pendente. Os estoques estão em situação adequada. ✔</div>';
  }
  $('#genRecs').addEventListener('click', async () => {
    const btn = $('#genRecs'); btn.disabled = true;
    try { const r = await api('recomendacoes/gerar', { method: 'POST', body: {} }); toast(`Análise atualizada: ${r.pendentes} recomendação(ões) pendente(s).`); await carregarRecomendacoes(); }
    catch (e) { toast(e.message, true); } finally { btn.disabled = false; }
  });
  $('#recs').addEventListener('click', async (ev) => {
    const dec = ev.target.closest('[data-dec]'), an = ev.target.closest('[data-analise]');
    try {
      if (dec) {
        await api(`recomendacoes/${dec.dataset.id}/decidir`, { method: 'POST', body: { status: dec.dataset.dec } });
        toast(dec.dataset.dec === 'ACEITA' ? 'Sugestão aceita e registrada.' : 'Sugestão ignorada.');
        await carregarRecomendacoes();
      }
      if (an) {
        const alvo = $('#det-' + an.dataset.id);
        if (alvo.innerHTML) { alvo.innerHTML = ''; return; }
        const d = await api(`produtos/${an.dataset.analise}/analise`), a = d.analise;
        const mx = Math.max(1, ...d.vendas_diarias.map((v) => v.quantidade));
        const f = (v, suf = '') => v === null || v === undefined ? '—' : String(v).replace('.', ',') + suf;
        alvo.innerHTML = `<div class="explain"><b>Como chegamos a esta sugestão</b><div class="metrics">
          <div><small>Demanda diária prevista</small><b>${f(a.demanda_diaria_prevista)}</b></div>
          <div><small>Cobertura do estoque</small><b>${f(a.dias_cobertura, ' dias')}</b></div>
          <div><small>Prazo de reposição</small><b>${a.prazo_entrega_dias} dias</b></div>
          <div><small>Ponto de pedido</small><b>${a.ponto_de_pedido} un.</b></div>
          <div><small>Tendência (14 dias)</small><b>${f(a.tendencia_percentual, '%')}</b></div>
          <div><small>Quantidade sugerida</small><b>${a.quantidade_sugerida} un.</b></div></div>
          <small>Vendas diárias nos últimos 30 dias</small><div class="mini-chart">${d.vendas_diarias.map((v) => `<i title="${v.data}: ${v.quantidade}" style="height:${Math.max(2, Math.round(v.quantidade / mx * 100))}%"></i>`).join('')}</div>
          <p style="margin:10px 0 0">Esta é uma sugestão estatística de apoio. A decisão final de compra é do gestor.</p></div>`;
      }
    } catch (e) { toast(e.message, true); }
  });

  // -------------------------------------------------------------- usuários
  async function carregarUsuarios() {
    const lista = await api('usuarios');
    $('#userRows').innerHTML = lista.map((u) => {
      const eu = state.user && u.id === state.user.id;
      const papeis = ['OPERADOR', 'GESTOR', 'ADMINISTRADOR'].map((p) => `<option value="${p}" ${p === u.papel ? 'selected' : ''}>${PAPEIS[p]}</option>`).join('');
      return `<tr><td>${esc(u.nome)}${eu ? ' <small>(você)</small>' : ''}</td><td>${esc(u.email)}</td>
        <td><select data-papel="${u.id}" ${eu ? 'disabled' : ''}>${papeis}</select></td>
        <td><span class="badge ${u.ativo ? 'badge-green' : 'badge-gray'}">${u.ativo ? 'Ativo' : 'Inativo'}</span></td>
        <td>${eu ? '' : `<button class="btn btn-outline btn-sm" data-toggle="${u.id}" data-ativo="${u.ativo}">${u.ativo ? 'Desativar' : 'Reativar'}</button>`}</td></tr>`;
    }).join('');
  }
  $('#saveUser').addEventListener('click', async () => {
    hideError('#userError');
    const btn = $('#saveUser'); btn.disabled = true;
    try {
      await api('usuarios', { method: 'POST', body: { nome: $('#uNome').value, email: $('#uEmail').value, senha: $('#uSenha').value, papel: $('#uPapel').value } });
      toast('Usuário criado com sucesso.');
      ['#uNome', '#uEmail', '#uSenha'].forEach((i) => { $(i).value = ''; });
      await carregarUsuarios();
    } catch (e) { showError('#userError', e); } finally { btn.disabled = false; }
  });
  $('#userRows').addEventListener('click', async (ev) => {
    const t = ev.target.closest('[data-toggle]');
    if (!t) return;
    try { await api('usuarios/' + t.dataset.toggle, { method: 'PATCH', body: { ativo: t.dataset.ativo !== 'true' } }); await carregarUsuarios(); }
    catch (e) { toast(e.message, true); }
  });
  $('#userRows').addEventListener('change', async (ev) => {
    const sel = ev.target.closest('[data-papel]');
    if (!sel) return;
    try { await api('usuarios/' + sel.dataset.papel, { method: 'PATCH', body: { papel: sel.value } }); toast('Perfil atualizado.'); }
    catch (e) { toast(e.message, true); await carregarUsuarios(); }
  });

  // ------------------------------------------------------------ inicialização
  (async () => {
    if (!state.token) return;
    try { entrarNoApp(await api('auth/me')); } catch (e) { sair(); }
  })();
})();
