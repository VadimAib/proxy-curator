                                                                 
                                                                        
                                                                            
  
                                                                      
                                                                          
                                                                        
                                      
  
                                                                     
                                                                        
                                                              
                                                                     
                     
  
                                                                        
                                                                     
                                                                    
                                                                         
  
                                                                            
                                                                        
                                      
  
                                                                 

(function () {
  'use strict';

  let logsFiles = [];                                                 
  let logsCurrent = null;                              
  let logsCleanDays = 14;                                                      
  let logsStatusIsNote = true;                                                        

                                                                          
                                                                     
                                                      
  const LOGS_ERR_KEYS = {
    unknown_log: 'logs_err_unknown_log',
    not_found: 'logs_err_not_found',
    io_error: 'logs_err_io_error',
    run_in_progress: 'logs_err_run_in_progress',
    bad_request: 'logs_err_bad_request',
    confirm_required: 'logs_err_confirm_required',
  };

                                                                        
                        
  function logsErrMessage(data, fallbackKey) {
    if (data && data.code && LOGS_ERR_KEYS[data.code]) {
      return T(LOGS_ERR_KEYS[data.code]) + (data.detail ? ' ' + data.detail : '');
    }
    const errs = (data && data.errors) || [];
    if (errs.length) return T(fallbackKey || 'logs_delete_fail') + ': ' + errs.join('; ');
    return (data && data.error) || T(fallbackKey || 'logs_delete_fail');
  }

  function logsFormatSize(bytes) {
    const n = Number(bytes) || 0;
    if (n < 1024) return n + ' B';
    const units = ['KB', 'MB', 'GB'];
    let v = n / 1024;
    let i = 0;
    while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
    return (v >= 10 ? Math.round(v) : v.toFixed(1)) + ' ' + units[i];
  }

  function logsFormatTime(stamp) {
    if (!stamp) return '';
    try { return new Date(stamp * 1000).toLocaleString(); } catch (e) { return ''; }
  }

                                                                        
                                                                              
                                                                   
                                  
  function logsSetStatus(text, note) {
    const title = document.getElementById('logs-title');
    if (title) title.textContent = text;
    logsStatusIsNote = note !== false;
  }

  function logsSetNote() {
    logsSetStatus(T('logs_none'), true);
  }

                                                                   
                                                                            
  function logsUpdateDeleteButton() {
    const btn = document.getElementById('btn-logs-delete');
    if (btn) btn.disabled = !logsCurrent;
  }

                                                                          
                                                                       
                                                             
  function logsIsRunLog(name) {
    return name === 'ui_run.log'
      || (String(name).startsWith('run_') && String(name).endsWith('.log'));
  }

                                                                          
                                        
  function logsOldCandidates(days) {
    const cutoff = Date.now() - days * 86400000;
    return logsFiles
      .filter(f => logsIsRunLog(f.name) && (f.mtime || 0) * 1000 < cutoff)
      .map(f => f.name);
  }

  function logsRenderList() {
    const list = document.getElementById('logs-list');
    if (!list) return;
    if (!logsFiles.length) {
      list.innerHTML = '<div class="logs-note">' + escapeHtmlStr(T('logs_empty')) + '</div>';
      return;
    }
    list.innerHTML = logsFiles.map(f => {
      const active = logsCurrent === f.name ? ' active' : '';
      const meta = logsFormatSize(f.size) + ' · ' + logsFormatTime(f.mtime);
      return '<button type="button" class="logs-item' + active + '" data-log-name="'
        + escapeHtmlStr(f.name) + '"><span class="logs-item-name">'
        + escapeHtmlStr(f.name) + '</span><span class="logs-item-meta">'
        + escapeHtmlStr(meta) + '</span></button>';
    }).join('');
  }

                                                                       
                                                                       
                                
  function logsUpdateCleanTooltip() {
    const btn = document.getElementById('btn-logs-clean');
    if (btn) btn.title = Tf('tt_logs_clean', { days: logsCleanDays });
  }

  async function refreshLogs() {
    const list = document.getElementById('logs-list');
    if (!list) return;
    try {
      const resp = await api('/api/logs');
      const data = await resp.json();
      logsFiles = data.files || [];
      if (typeof data.clean_days === 'number' && data.clean_days > 0) {
        logsCleanDays = data.clean_days;
      }
      logsUpdateCleanTooltip();
      logsRenderList();
      logsUpdateDeleteButton();
    } catch (e) {
                                                                        
      list.innerHTML = '<div class="logs-note">'
        + escapeHtmlStr(T('logs_load_fail') + ' ' + String(e)) + '</div>';
    }
  }

  async function openLogFile(name) {
    const view = document.getElementById('logs-view');
    if (!view || !name) return;
    logsCurrent = name;
    logsRenderList();
    logsUpdateDeleteButton();
    view.innerHTML = '<div class="logs-note">' + escapeHtmlStr(T('logs_loading')) + '</div>';
    try {
      const resp = await api('/api/log?file=' + encodeURIComponent(name));
      const data = await resp.json();
      if (!resp.ok || data.ok === false) {
        view.innerHTML = '<div class="logs-note">'
          + escapeHtmlStr(logsErrMessage(data, 'logs_load_fail')) + '</div>';
        logsSetStatus(logsErrMessage(data, 'logs_load_fail'));
        return;
      }
      const lines = data.lines || [];
      view.innerHTML = lines.length
        ? lines.map(l => '<div class="log-line">' + escapeHtml(l) + '</div>').join('')
        : '<div class="logs-note">'
          + escapeHtmlStr(data.truncated ? T('logs_truncated') : T('logs_empty_file')) + '</div>';
      const parts = [name, logsFormatSize(data.size || 0), logsFormatTime(data.mtime)];
      if (data.truncated) parts.push(T('logs_truncated'));
      logsSetStatus(parts.filter(Boolean).join(' · '), false);
      view.scrollTop = view.scrollHeight;
    } catch (e) {
      view.innerHTML = '<div class="logs-note">'
        + escapeHtmlStr(T('logs_load_fail') + ' ' + String(e)) + '</div>';
    }
  }

  async function deleteLogFile() {
    if (!logsCurrent) return;
    if (!confirm(Tf('logs_confirm_delete', { name: logsCurrent }))) return;
    const view = document.getElementById('logs-view');
    try {
      const resp = await api('/api/logs/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: logsCurrent }),
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        logsSetStatus(logsErrMessage(data, 'logs_delete_fail'));
        return;
      }
      logsCurrent = null;
      if (view) view.innerHTML = '';
      logsSetNote();
      logsUpdateDeleteButton();
      refreshLogs();
    } catch (e) {
      logsSetStatus(T('logs_delete_fail') + ' ' + String(e));
    }
  }

  async function cleanOldLogs() {
    const days = logsCleanDays;
                                                                      
    const names = logsOldCandidates(days);
    if (!names.length) {
      logsSetStatus(Tf('logs_deleted', { n: 0 }), false);
      return;
    }
    const question = Tf('logs_confirm_clean', { days: days }) + '\n' + names.join('\n');
    if (!confirm(question)) return;
    try {
      const resp = await api('/api/logs/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
                                                                             
                                                                 
        body: JSON.stringify({ older_than_days: days, confirm: true }),
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        logsSetStatus(logsErrMessage(data, 'logs_delete_fail'));
        return;
      }
      logsSetStatus(Tf('logs_deleted', { n: (data.deleted || []).length }), false);
      refreshLogs();
    } catch (e) {
      logsSetStatus(T('logs_delete_fail') + ' ' + String(e));
    }
  }

  async function openLogsFolder() {
    try {
      const resp = await api('/api/logs/open-folder', { method: 'POST' });
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        logsSetStatus(logsErrMessage(data, 'logs_folder_fail'));
      }
    } catch (e) {
      logsSetStatus(T('logs_folder_fail') + ' ' + String(e));
    }
  }

                                          
  document.addEventListener('click', e => {
    const item = e.target && e.target.closest ? e.target.closest('[data-log-name]') : null;
    if (!item) return;
    openLogFile(item.dataset.logName);
  });

                                                                 
                                                                   
                 
  window.Logs = {
    refresh: refreshLogs,
    open: openLogFile,
    remove: deleteLogFile,
    clean: cleanOldLogs,
    openFolder: openLogsFolder,
                                                                    
    langChanged: function () {
      if (logsStatusIsNote) logsSetNote();
    },
    setNote: logsSetNote,
  };
})();
