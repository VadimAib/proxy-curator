                                                                      
                                                                           
                                                                        
                                                                    
  
                                                                            
                                                                             
                                                                           
                                                                           
                                                             
  
                                                                      
                                                                        
                                                              
                                                                     
                     
  
                                                                        
                                                                            
                                                                         
                                              
  
                                                                      
                                                                       
                                            

(function () {
  'use strict';

  const GUIDE_URL = '/guide.json';
                                                                           
                                                                    
                                
  const GUIDE_VERSION = 1;
  let guide = null;                                    
  let guidePromise = null;                             
  let guideIndex = null;                                    
  let guideHashLock = false;
  let guideFailed = false;                           
  let guideFailedAt = 0;                                                     

                                                                      
                                                                 
                                                                
                 
  const GUIDE_RETRY_MS = 30000;

  function guideLang(value, lang) {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value;
    return value[lang] || value.en || '';
  }

  function guideT(value) {
    return guideLang(value, LANG);
  }

                                                                           
                                
  function guideAlt(value) {
    return guideLang(value, LANG === 'ru' ? 'en' : 'ru');
  }

                                                                
                                                                           
                                                         
  function guideInline(text) {
    let html = escapeHtmlStr(text);
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\[([^\]]+)\]\(([a-z0-9-]+)(#[a-z0-9-]+)?\)/g, (m, label, id, anchor) =>
      '<a href="#guide/' + id + (anchor || '') + '" data-guide-article="' + id + '"'
      + (anchor ? ' data-guide-anchor="' + anchor + '"' : '') + '>' + label + '</a>');
    return html;
  }

                                                                             
                                                                         
                                                                      
                                   
  function guideBlockText(block, picker) {
    const text = picker || guideT;
    switch (block.t) {
      case 'p': case 'h': case 'note':
        return text(block.text);
      case 'ul': case 'ol':
        return (block.items || []).map(text).join(' ');
      case 'table':
        return (block.head || []).map(text).join(' ')
          + ' ' + (block.rows || []).map(r => r.map(text).join(' ')).join(' ');
      case 'code':
        return String(block.text || '');
      case 'links':
        return (block.items || []).map(text).join(' ');
      case 'ui':
        return text(block.label);
      default:
        return '';
    }
  }

  function guideLoad() {
    if (guidePromise) return guidePromise;
    guidePromise = fetch(GUIDE_URL, { cache: 'no-store' })
      .then(resp => {
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        return resp.json();
      })
      .then(data => {
        guide = data;
        guideFailed = false;
        if (Number(data.version) !== GUIDE_VERSION) {
          console.warn('[guide] версия guide.json не совпадает с модулем:',
            data.version, 'ожидалась', GUIDE_VERSION);
        }
        guideBuildIndex();
      })
      .catch(err => {
        guide = null;
        guideFailed = true;
        guideFailedAt = Date.now();
                                                                      
                                                         
        guidePromise = null;
        console.warn('[guide] guide.json не загрузился:', err);
      });
    return guidePromise;
  }

  function guideBuildIndex() {
    if (!guide) return;
    guideIndex = (guide.articles || []).map(a => {
      const raw = [guideT(a.title), guideT(a.summary)]
        .concat((a.blocks || []).map(b => guideBlockText(b))).join(' ');
      const altRaw = [guideAlt(a.title), guideAlt(a.summary)]
        .concat((a.blocks || []).map(b => guideBlockText(b, guideAlt))).join(' ');
      return {
        id: a.id,
        title: guideT(a.title),
        altTitle: guideAlt(a.title),
        summary: guideT(a.summary),
        raw: raw,
        text: raw.toLowerCase(),
        altRaw: altRaw,
        altText: altRaw.toLowerCase(),
      };
    });
  }

  function guideRenderTree() {
    const nav = document.getElementById('guide-tree');
    if (!nav || !guide) return false;
                                                                       
                                                                         
                                                                 
    if (nav.dataset.guideLang === LANG) return false;
    const articles = guide.articles || [];
    let html = '';
    for (const cat of guide.categories || []) {
      const inCat = articles.filter(a => a.category === cat.id);
      if (!inCat.length) continue;
      html += '<div class="guide-cat"><div class="guide-cat-title">'
        + guideInline(guideT(cat.title)) + '</div>';
      for (const a of inCat) {
                                                                       
                                                                    
                                                                             
        html += '<button type="button" class="guide-link" data-guide-article="'
          + a.id + '">' + guideInline(guideT(a.title)) + '</button>';
      }
      html += '</div>';
    }
    nav.innerHTML = html;
    nav.dataset.guideLang = LANG;
    return true;
  }

                                                                    
                                              
  function guideTreeHasFocus() {
    const nav = document.getElementById('guide-tree');
    return !!(nav && nav.contains(document.activeElement));
  }

                                                                       
                                                   
  function guideFocusActiveLink() {
    const nav = document.getElementById('guide-tree');
    if (!nav) return;
    const link = nav.querySelector('.guide-link.active') || nav.querySelector('.guide-link');
    if (link) link.focus();
  }

  function guideRenderArticle(article) {
    const el = document.getElementById('guide-article');
    if (!el) return;
                                                                          
                                                      
    const wide = (article.blocks || []).some(b => b.t === 'table');
    el.className = 'guide-article' + (wide ? ' guide-article--wide' : '');
    let html = '<h2>' + guideInline(guideT(article.title)) + '</h2>';
    if (article.summary) html += '<p>' + guideInline(guideT(article.summary)) + '</p>';
    for (const block of article.blocks || []) {
      switch (block.t) {
        case 'p':
          html += '<p>' + guideInline(guideT(block.text)) + '</p>';
          break;
        case 'h':
          html += '<h3 id="g-' + block.id + '">' + guideInline(guideT(block.text))
            + '<a class="guide-anchor" href="#guide/' + article.id + '/' + block.id
            + '" aria-hidden="true">#</a></h3>';
          break;
        case 'ul': case 'ol': {
          html += '<' + block.t + '>';
          for (const item of block.items || []) html += '<li>' + guideInline(guideT(item)) + '</li>';
          html += '</' + block.t + '>';
          break;
        }
        case 'table': {
          html += '<table><thead><tr>';
          for (const h of block.head || []) html += '<th>' + guideInline(guideT(h)) + '</th>';
          html += '</tr></thead><tbody>';
          for (const row of block.rows || []) {
            html += '<tr>';
            for (const cell of row) html += '<td>' + guideInline(guideT(cell)) + '</td>';
            html += '</tr>';
          }
          html += '</tbody></table>';
          break;
        }
        case 'code':
          html += '<pre><code>' + escapeHtmlStr(block.text) + '</code></pre>';
          break;
        case 'note':
                                                                            
                                                                             
                           
          html += '<div class="guide-note' + (block.kind ? ' guide-note--' + block.kind : '') + '">'
            + guideInline(guideT(block.text)) + '</div>';
          break;
        case 'links': {
          html += '<div class="guide-related"><div class="guide-related-title">'
            + escapeHtmlStr(T('guide_related')) + '</div><ul>';
          for (const item of block.items || []) {
            html += '<li><a href="#guide/' + item.id + '" data-guide-article="' + item.id + '">'
              + guideInline(guideT(item.text)) + '</a></li>';
          }
          html += '</ul></div>';
          break;
        }
        case 'ui':
                                                                           
                                                                             
                                                                              
          html += '<button type="button" class="guide-ui-link" data-guide-tab="'
            + escapeHtmlStr(block.tab || '') + '"'
            + (block.field ? ' data-guide-field="' + escapeHtmlStr(block.field) + '"' : '')
            + '>' + guideInline(guideT(block.label)) + '</button>';
          break;
        default:
          break;
      }
    }
    el.innerHTML = html;
  }

  function guideMarkActive(id) {
    document.querySelectorAll('#guide-tree .guide-link').forEach(el => {
      el.classList.toggle('active', el.dataset.guideArticle === id);
    });
  }

                                                                    
                                                                
                                            
  function guideAnnounce(text) {
    const el = document.getElementById('guide-announce');
    if (el) el.textContent = text;
  }

  function guideHash() {
    const raw = location.hash.replace(/^#/, '');
    if (!raw.startsWith('guide/')) return null;
    const parts = raw.slice('guide/'.length).split('/');
    return { id: parts[0] || '', anchor: parts[1] || '' };
  }

  function guideOpen(id, anchor) {
    const el = document.getElementById('guide-article');
    if (!el || !guide) return;
    const article = (guide.articles || []).find(a => a.id === id);
    if (!article) {
      el.innerHTML = '<div class="guide-status">' + escapeHtmlStr(T('guide_article_missing')) + '</div>';
      guideAnnounce(T('guide_article_missing'));
      return;
    }
    guideRenderArticle(article);
    guideMarkActive(article.id);
    guideAnnounce(guideT(article.title));
    const want = '#guide/' + article.id + (anchor ? '/' + anchor : '');
    if (location.hash !== want) {
                                                                           
                                                       
      guideHashLock = true;
      location.hash = want;
      setTimeout(() => { guideHashLock = false; }, 0);
    }
    if (anchor) {
      const target = document.getElementById('g-' + anchor);
      const main = document.querySelector('.guide-main');
                                                                        
                                                                       
      if (target && main) {
        const mainRect = main.getBoundingClientRect();
        const targetRect = target.getBoundingClientRect();
        main.scrollTop += (targetRect.top - mainRect.top) - 12;
      }
    } else {
      const main = document.querySelector('.guide-main');
      if (main) main.scrollTop = 0;
    }
  }

  function guideJump(id, anchor) {
    switchTab('readme');
    if (guide) {
      guideOpen(id, anchor || '');
      return;
    }
    guideLoad().then(() => guideOpen(id, anchor || ''));
  }

                                                                           
  function guideTipTarget(key) {
    if (!key || !guide || !guide.tips) return null;
    return guide.tips[key] || null;
  }

                                                                              
                                                                        
  function guideTipLink(key) {
    const target = guideTipTarget(key);
    if (!target) return null;
    const more = document.createElement('a');
    more.className = 'guide-tip-link';
    more.textContent = T('guide_more');
                                                                           
                                            
    more.href = '#guide/' + target.replace('#', '/');
    more.addEventListener('click', ev => {
      ev.preventDefault();
      ev.stopPropagation();
      if (typeof hideTip === 'function') hideTip();
      const parts = target.split('#');
      guideJump(parts[0], parts[1] || '');
    });
    return more;
  }

  function guideShow() {
    const el = document.getElementById('guide-article');
    if (!el) return;
    if (!guide) {
                                                                           
                                                                             
      if (guideFailed && Date.now() - guideFailedAt < GUIDE_RETRY_MS) {
        el.innerHTML = '<div class="guide-status">' + escapeHtmlStr(T('guide_error')) + '</div>';
        return;
      }
      el.innerHTML = '<div class="guide-status">' + escapeHtmlStr(T('guide_loading')) + '</div>';
      guideLoad().then(() => guideShow());
      return;
    }
                                                                         
                                                                          
                   
    const focusInTree = guideTreeHasFocus();
    const rebuilt = guideRenderTree();
    const h = guideHash();
    guideOpen(h ? h.id : 'quickstart', h ? h.anchor : '');
    if (rebuilt && focusInTree) guideFocusActiveLink();
  }

                                                                        
                                   
  function guidePlain(text) {
    return String(text)
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/`([^`]+)`/g, '$1');
  }

  function guideSnippet(item, tokens) {
                                                                            
                                                                
    let source = item.raw;
    let lower = item.text;
    let pos = -1;
    for (const t of tokens) {
      const p = lower.indexOf(t);
      if (p >= 0 && (pos < 0 || p < pos)) pos = p;
    }
    if (pos < 0) {
      source = item.altRaw;
      lower = item.altText;
      for (const t of tokens) {
        const p = lower.indexOf(t);
        if (p >= 0 && (pos < 0 || p < pos)) pos = p;
      }
    }
    if (pos < 0) return guidePlain(item.summary);
    const start = Math.max(0, pos - 60);
    const end = Math.min(source.length, pos + 120);
    return (start > 0 ? '…' : '') + guidePlain(source.slice(start, end))
      + (end < source.length ? '…' : '');
  }

  function guideHighlight(text, tokens) {
    let html = escapeHtmlStr(text);
    for (const t of tokens) {
      const safe = escapeHtmlStr(t).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      html = html.replace(new RegExp('(' + safe + ')', 'gi'), '<mark>$1</mark>');
    }
    return html;
  }

  function guideSearchInput(value) {
    const box = document.getElementById('guide-results');
    const tree = document.getElementById('guide-tree');
    if (!box || !tree) return;
    const query = String(value || '').trim().toLowerCase();
    if (!query) {
      box.innerHTML = '';
      box.classList.add('hidden');
      tree.classList.remove('hidden');
      guideAnnounce('');
      return;
    }
    if (!guide || !guideIndex) return;
    const tokens = query.split(/\s+/).filter(Boolean);
    const hits = [];
    for (const item of guideIndex) {
      const title = item.title.toLowerCase();
      const altTitle = item.altTitle.toLowerCase();
                                                                              
                                                           
      const inTitle = tokens.every(t => title.includes(t) || altTitle.includes(t));
      const inText = tokens.every(t => item.text.includes(t) || item.altText.includes(t));
      if (!inTitle && !inText) continue;
      const score = (inTitle ? 2 : 0) + tokens.filter(t => title.includes(t)).length;
      hits.push({ item: item, score: score });
    }
    hits.sort((a, b) => b.score - a.score);
    tree.classList.add('hidden');
    box.classList.remove('hidden');
    if (!hits.length) {
      box.innerHTML = '<div class="guide-empty">'
        + escapeHtmlStr(T('guide_no_results').replace('{q}', value)) + '</div>';
      guideAnnounce(T('guide_no_results').replace('{q}', value));
      return;
    }
    let html = '<div class="guide-results-title">'
      + escapeHtmlStr(Tf('guide_results', { n: hits.length })) + '</div>';
    for (const hit of hits.slice(0, 30)) {
      html += '<button type="button" class="guide-hit" data-guide-article="'
        + hit.item.id + '"><span class="guide-hit-title">'
        + guideHighlight(hit.item.title, tokens) + '</span><span class="guide-hit-snippet">'
        + guideHighlight(guideSnippet(hit.item, tokens), tokens) + '</span></button>';
    }
    box.innerHTML = html;
    guideAnnounce(Tf('guide_results', { n: hits.length }));
  }

  function guideFocusSearch() {
    switchTab('readme');
    const input = document.getElementById('guide-search');
    if (input) { input.focus(); input.select(); }
  }

                                                                     
  document.addEventListener('click', e => {
    const ui = e.target && e.target.closest ? e.target.closest('[data-guide-tab]') : null;
    if (ui) {
      e.preventDefault();
      guideOpenUi(ui.dataset.guideTab, ui.dataset.guideField || '');
      return;
    }
    const link = e.target && e.target.closest ? e.target.closest('[data-guide-article]') : null;
    if (!link) return;
    e.preventDefault();
    guideJump(link.dataset.guideArticle, link.dataset.guideAnchor || '');
  });

                                                                           
                                                                         
  function guideOpenUi(tab, field) {
    if (!tab) return;
    switchTab(tab);
    if (!field) return;
    const el = document.getElementById(field);
    if (!el) {
                                                                           
                                                                  
      guideAnnounce(T('guide_ui_missing') + ' ' + field);
      console.warn('[guide] цель живой ссылки не найдена:', field);
      return;
    }
    el.scrollIntoView({ block: 'center' });
    try { el.focus({ preventScroll: true }); } catch (e) { el.focus(); }
    el.classList.add('pc-flash');
    setTimeout(() => el.classList.remove('pc-flash'), 2600);
  }

                                                                           
                                                                  

                                            
  document.addEventListener('keydown', e => {
    const tag = (document.activeElement && document.activeElement.tagName) || '';
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      guideFocusSearch();
    } else if (e.key === '/' && !/^(INPUT|TEXTAREA|SELECT)$/.test(tag)) {
      e.preventDefault();
      guideFocusSearch();
    }
  });

                                                                            
                                                                     
                 
  document.addEventListener('input', e => {
    const input = e.target && e.target.closest ? e.target.closest('#guide-search') : null;
    if (!input) return;
    guideSearchInput(input.value);
  });

  window.addEventListener('hashchange', () => {
    if (guideHashLock) return;
    const h = guideHash();
    if (!h) return;
                                                                         
                                                                              
    switchTab('readme');
  });

                                                                             
                                               
  window.addEventListener('load', () => {
    if (guideHash()) switchTab('readme');
  });

                                                                 
                                                                  
                 
  window.Guide = {
    load: guideLoad,
    show: guideShow,
    jump: guideJump,
    tipLink: guideTipLink,
                                                                   
                                 
    langChanged: function () {
      if (!guide) return;
      guideBuildIndex();
      guideRenderTree();
      const input = document.getElementById('guide-search');
      if (input && input.value) guideSearchInput(input.value);
    },
  };
})();
