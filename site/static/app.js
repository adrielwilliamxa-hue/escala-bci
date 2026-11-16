(function () {
  const popup = document.querySelector('#edit-popup');

  function pad2(n) { return String(n).padStart(2, '0'); }
  function parseBR(dateStr) {
    const [d, m, y] = dateStr.split('/').map(Number);
    return new Date(y, m - 1, d);
  }
  function formatBR(date) {
    return `${pad2(date.getDate())}/${pad2(date.getMonth() + 1)}/${date.getFullYear()}`;
  }

  if (popup) {
    const forms = popup.querySelectorAll('.form');
    const opts = popup.querySelectorAll('.opt');
    const calContainer = document.querySelector('table.cal');
    let activePerson = null;

    function closePopup() {
      popup.classList.remove('open');
      forms.forEach(f => f.classList.remove('open'));
      opts.forEach(o => o.style.display = 'flex');
      popup.querySelector('.divider').style.display = 'block';
    }

    function recomputeFeriasFim() {
      const inicioVal = document.querySelector('#ferias-inicio').value;
      if (!inicioVal) return;
      const inicio = parseBR(inicioVal);
      const duracao = document.querySelector('#ferias-duracao').value;
      let fim;
      if (duracao === '20') {
        fim = new Date(inicio); fim.setDate(fim.getDate() + 19);
      } else {
        fim = new Date(inicio.getFullYear(), inicio.getMonth() + 1, inicio.getDate() - 1);
      }
      document.querySelector('#ferias-fim').value = formatBR(fim);
    }
    document.querySelector('#ferias-duracao').addEventListener('change', recomputeFeriasFim);

    function wireOutroBrigadista(selectId, inputId) {
      const select = document.querySelector(selectId);
      const input = document.querySelector(inputId);
      select.addEventListener('change', () => {
        const isOutro = select.value === '__outro__';
        input.style.display = isOutro ? 'block' : 'none';
        if (isOutro) input.focus();
      });
    }
    wireOutroBrigadista('#dia-select', '#dia-select-outro');
    wireOutroBrigadista('#ferias-select', '#ferias-select-outro');

    calContainer.addEventListener('click', (e) => {
      const p = e.target.closest('.person');
      if (!p) return;
      e.stopPropagation();
      const cell = p.closest('td');
      const alreadyOpenHere = popup.classList.contains('open') && activePerson === p;
      closePopup();
      activePerson = p;
      cell.appendChild(popup);

      const nome = p.dataset.name;
      const dateStr = p.dataset.date;
      const [y, m, day] = dateStr.split('-');
      document.querySelector('#dia-label').textContent = `Substituto em ${day}/${m}`;
      document.querySelector('#dia-select').dataset.pessoa = nome;
      document.querySelector('#dia-select').dataset.data = dateStr;
      document.querySelector('#ferias-select').dataset.pessoa = nome;
      document.querySelector('#ferias-inicio').value = `${day}/${m}/${y}`;
      document.querySelector('#ferias-duracao').value = '20';
      recomputeFeriasFim();

      const cellRect = cell.getBoundingClientRect();
      const tableRect = cell.closest('table').getBoundingClientRect();
      const wouldOverflow = (cellRect.left + p.offsetLeft + 224) > tableRect.right;
      popup.style.left = wouldOverflow ? 'auto' : (p.offsetLeft + 'px');
      popup.style.right = wouldOverflow ? '6px' : 'auto';
      if (!alreadyOpenHere) popup.classList.add('open');
    });

    opts.forEach(opt => {
      opt.addEventListener('click', (e) => {
        e.stopPropagation();
        opts.forEach(o => o.style.display = 'none');
        popup.querySelector('.divider').style.display = 'none';
        forms.forEach(f => f.classList.toggle('open', f.dataset.form === opt.dataset.action));
      });
    });

    document.querySelector('[data-form="dia"] .save').addEventListener('click', async (e) => {
      e.stopPropagation();
      const sel = document.querySelector('#dia-select');
      const outro = document.querySelector('#dia-select-outro');
      const substituto = sel.value === '__outro__' ? outro.value.trim() : sel.value;
      const resp = await fetch('/api/dia', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pessoa: sel.dataset.pessoa, data: sel.dataset.data, substituto }),
      });
      if (resp.ok) location.reload(); else alert('Erro ao salvar a troca do dia.');
    });

    document.querySelector('[data-form="ferias"] .save').addEventListener('click', async (e) => {
      e.stopPropagation();
      const sel = document.querySelector('#ferias-select');
      const outro = document.querySelector('#ferias-select-outro');
      const substituto = sel.value === '__outro__' ? outro.value.trim() : sel.value;
      const inicio = document.querySelector('#ferias-inicio').value;
      const duracao = document.querySelector('#ferias-duracao').value;
      const resp = await fetch('/api/ferias', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pessoa: sel.dataset.pessoa, inicio, duracao, substituto }),
      });
      if (resp.ok) location.reload(); else alert('Erro ao marcar férias.');
    });

    document.addEventListener('click', closePopup);
    popup.addEventListener('click', (e) => e.stopPropagation());
  }

  const calTable = document.querySelector('table.cal');
  if (calTable) {
    calTable.addEventListener('click', async (e) => {
      const toggle = e.target.closest('.fds-toggle');
      if (!toggle) return;
      e.stopPropagation();
      const novaPos = toggle.dataset.posFds === '1' ? 2 : 1;
      const resp = await fetch('/api/fds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome_mes: toggle.dataset.mes, dia: toggle.dataset.dia, pos_fds: novaPos }),
      });
      if (resp.ok) location.reload(); else alert('Erro ao trocar a dupla do fim de semana.');
    });
  }

  const renamePopup = document.querySelector('#rename-popup');
  if (renamePopup) {
    function closeRenamePopup() { renamePopup.classList.remove('open'); }
    document.querySelector('#team-blocks').addEventListener('click', (e) => {
      const row = e.target.closest('.team-row');
      if (!row) return;
      e.stopPropagation();
      const nome = row.dataset.name;
      closeRenamePopup();
      row.appendChild(renamePopup);
      document.querySelector('#ano-label').textContent = `Novo nome para ${nome}`;
      document.querySelector('#ano-input').value = nome;
      document.querySelector('#ano-input').dataset.nomeAntigo = nome;
      document.querySelector('#ano-input-completo').value = row.dataset.nomeCompleto || '';
      renamePopup.classList.add('open');
    });
    renamePopup.querySelector('.save').addEventListener('click', async (e) => {
      e.stopPropagation();
      const input = document.querySelector('#ano-input');
      const inputCompleto = document.querySelector('#ano-input-completo');
      const resp = await fetch('/api/renomear', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nome_antigo: input.dataset.nomeAntigo,
          nome_novo: input.value,
          nome_completo: inputCompleto.value,
        }),
      });
      if (resp.ok) location.reload(); else alert('Erro ao renomear.');
    });
    renamePopup.addEventListener('click', (e) => e.stopPropagation());
    document.addEventListener('click', closeRenamePopup);
  }

  const btnPrint = document.querySelector('#btn-print');
  if (btnPrint) btnPrint.addEventListener('click', () => window.print());

  const anoSelect = document.querySelector('#ano-select');
  if (anoSelect) {
    anoSelect.addEventListener('change', () => {
      const url = new URL(window.location.href);
      url.searchParams.set('ano', anoSelect.value);
      window.location.href = url.toString();
    });
  }

  const mesTrabalhadosSelect = document.querySelector('#mes-trabalhados-select');
  if (mesTrabalhadosSelect) {
    const tabela = document.querySelector('#tabela-dias-trabalhados');
    function aplicarFiltro() {
      const valor = mesTrabalhadosSelect.value;
      tabela.querySelectorAll('[data-mes-idx]').forEach(cel => {
        cel.style.display = (valor === 'todos' || cel.dataset.mesIdx === valor) ? '' : 'none';
      });
    }
    mesTrabalhadosSelect.addEventListener('change', aplicarFiltro);
    aplicarFiltro();
  }

  const btnCertificados = document.querySelector('#btn-salvar-certificados');
  if (btnCertificados) {
    btnCertificados.addEventListener('click', async () => {
      const inputs = document.querySelectorAll('.cert-codigo-input');
      const certificados = Array.from(inputs).map(i => ({ pessoa: i.dataset.pessoa, codigo: i.value }));
      const resp = await fetch('/api/certificados', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ certificados }),
      });
      if (resp.ok) location.reload(); else alert('Erro ao salvar certificados.');
    });
  }

  document.querySelectorAll('.btn-remover').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      if (!confirm('Remover este registro? Essa ação não pode ser desfeita.')) return;
      const rota = btn.dataset.tipo === 'ferias' ? '/api/ferias/remover' : '/api/folga/remover';
      const resp = await fetch(rota, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: btn.dataset.id }),
      });
      if (resp.ok) location.reload(); else alert('Erro ao remover.');
    });
  });

  document.querySelectorAll('.btn-editar-substituto').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const form = document.querySelector(`.editar-substituto-form[data-id="${btn.dataset.id}"]`);
      form.style.display = form.style.display === 'none' ? 'flex' : 'none';
    });
  });

  document.querySelectorAll('.btn-salvar-substituto').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const form = btn.closest('.editar-substituto-form');
      const input = form.querySelector('.editar-substituto-input');
      const resp = await fetch('/api/ferias/editar-substituto', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: btn.dataset.id, substituto: input.value }),
      });
      if (resp.ok) location.reload(); else alert('Erro ao salvar o substituto.');
    });
  });
})();
