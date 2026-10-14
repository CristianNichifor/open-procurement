// The RO/EN toggle on the static pages. The language is carried in the address
// (?lang=en), not in storage: the site keeps nothing in the browser (see privacy.html),
// and a link to the English text should open the English text.
(() => {
  const pick = (lang) => {
    document.documentElement.lang = lang;
    document.title = document.body.dataset[lang === 'en' ? 'titleEn' : 'titleRo'];
    for (const b of document.querySelectorAll('[data-set-lang]')) {
      b.setAttribute('aria-pressed', String(b.dataset.setLang === lang));
    }
  };
  const params = new URLSearchParams(location.search);
  pick(params.get('lang') === 'en' ? 'en' : 'ro');
  for (const b of document.querySelectorAll('[data-set-lang]')) {
    b.addEventListener('click', () => {
      const lang = b.dataset.setLang;
      pick(lang);
      if (lang === 'en') params.set('lang', 'en'); else params.delete('lang');
      const query = params.toString();
      history.replaceState(null, '', location.pathname + (query ? `?${query}` : '') + location.hash);
    });
  }
})();
