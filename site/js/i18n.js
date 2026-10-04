// UI strings. Story titles/summaries come with the data; article headlines stay Turkish.
// A few strings contain markup on purpose; they're static, never user data.

export const TEXT = {
  tr: {
    subtitle: "Türkiye medyasının olaylara editoryal bakış açısını analiz eden tarafsız platform.",
    about: "Nedir?",
    aboutBody:
      "Yapay zeka ile <b>{n}</b> ulusal kaynağı tarayıp aynı olayı anlatan haberleri gruplayan analiz platformu. " +
      "Renkli çubuklar bir haberin iktidara yakın, ana akım/bağımsız ve muhalif basında ne kadar yer bulduğunu, " +
      "<b>Kör Noktalar</b> ise bir kesimin neredeyse hiç yer vermediği gündemleri gösterir. " +
      "Kaynakların nasıl sınıflandırıldığını sayfanın altındaki <b>Kaynaklar ve Metodoloji</b> bölümünde görebilirsiniz.",
    themeToggle: "Temayı değiştir",
    updated: "Son güncelleme",
    betaNote: "",
    timeframe: "Zaman aralığı",
    time1: "Bugün (24s)",
    time7: "Bu Hafta (7g)",
    time30: "Bu Ay (30g)",
    topics: "Konu filtresi",
    allStories: "Tüm Gündem",
    agenda: "Gündem",
    blindspots: "Kör Noktalar",
    blindspotsBody:
      "İktidara yakın ya da muhalif basının kapsamının <b>%10'un altında</b> kaldığı haberler. " +
      "Sadece en az 3 kaynağın yer verdiği haberler hesaba katılır.",
    missedByOpposition: "Muhalif Basının Atladıkları",
    missedByProgov: "İktidara Yakın Basının Atladıkları",
    oppCoverage: "Muhalif kapsamı",
    progovCoverage: "İktidara yakın kapsamı",
    noOppMiss: "Şu an muhalif basının atladığı bir gündem yok.",
    noProgovMiss: "Şu an iktidara yakın basının atladığı bir gündem yok.",
    moreBlindspots: "Diğer Kör Noktaları Gör",
    sources: (n) => `${n} kaynak`,
    articles: (n) => `${n} haber`,
    neutralSummary: "Tarafsız Özet",
    headlines: "Manşetler",
    noArticles: "Bu kesimden haber yok.",
    share: "Paylaş",
    copied: "Bağlantı kopyalandı",
    close: "Kapat",
    allTime: "Son 30 gün",
    storyGone: "Bu haber artık listede değil. Haberler 30 gün sonra arşivden düşer.",
    emptyWindow: "Bu zaman aralığında henüz gruplanmış haber yok.",
    tryWeek: "Bu haftaya bak",
    noData: "Veri yüklenemedi. Sayfayı yenilemeyi deneyin.",
    loading: "Yükleniyor…",
    methodology: "Kaynaklar ve Metodoloji",
    removed: "Listeden çıkarılan kaynaklar",
    whyGroup: "Neden bu grupta?",
    evidence: "Dayanak",
    status: { sourced: "Kaynaklı", review: "Değerlendirme sürüyor", disputed: "Tartışmalı" },
    footer: "Veriler {n} ulusal haber kaynağından RSS ile toplanmakta ve Google Gemini ile gruplanmaktadır. Medya şeffaflığı için geliştirilmiştir.",
    disclaimer: "Bu platform kullanıcı verisi toplamaz (çerez/KVKK onayı gerektirmez). Haber içeriklerinin telif hakları ilgili yayıncılara aittir.",
    sourceCode: "Kaynak kodu",
  },
  en: {
    subtitle: "An objective platform analyzing the editorial perspectives of Turkish media on current events.",
    about: "What is it?",
    aboutBody:
      "AI-powered media analysis scanning <b>{n}</b> national sources and grouping articles about the same event. " +
      "Colored bars show how much a story is covered by pro-government, mainstream/independent and opposition media, " +
      "while <b>Blindspots</b> show stories one side barely covers. " +
      "See <b>Sources &amp; Methodology</b> at the bottom for how outlets are classified.",
    themeToggle: "Toggle theme",
    updated: "Last updated",
    betaNote: "Article headlines are shown in their original Turkish.",
    timeframe: "Timeframe",
    time1: "Today (24h)",
    time7: "This Week (7d)",
    time30: "This Month (30d)",
    topics: "Topic filter",
    allStories: "All Stories",
    agenda: "Top Stories",
    blindspots: "Blindspots",
    blindspotsBody:
      "Stories where pro-government or opposition media coverage stays <b>below 10%</b>. " +
      "Only stories covered by at least 3 outlets are counted.",
    missedByOpposition: "Missed by Opposition Media",
    missedByProgov: "Missed by Pro-Gov Media",
    oppCoverage: "opposition coverage",
    progovCoverage: "pro-gov coverage",
    noOppMiss: "Currently no major blindspots for opposition media.",
    noProgovMiss: "Currently no major blindspots for pro-government media.",
    moreBlindspots: "View More Blindspots",
    sources: (n) => `${n} ${n === 1 ? "source" : "sources"}`,
    articles: (n) => `${n} ${n === 1 ? "article" : "articles"}`,
    neutralSummary: "Neutral Summary",
    headlines: "Headlines",
    noArticles: "No coverage from this side.",
    share: "Share",
    copied: "Link copied",
    close: "Close",
    allTime: "Last 30 days",
    storyGone: "This story is no longer listed. Stories drop out after 30 days.",
    emptyWindow: "No grouped stories in this timeframe yet.",
    tryWeek: "Show this week",
    noData: "Couldn't load the data. Try reloading the page.",
    loading: "Loading…",
    methodology: "Sources & Methodology",
    removed: "Removed outlets",
    whyGroup: "Why this group?",
    evidence: "Evidence",
    status: { sourced: "Sourced", review: "Under review", disputed: "Disputed" },
    footer: "Data is aggregated from {n} national RSS feeds and clustered with Google Gemini. Developed for media transparency.",
    disclaimer: "We do not track user data (no cookies, no consent banner needed). News content belongs to the respective publishers.",
    sourceCode: "Source code",
  },
};

export const GROUP_LABEL = {
  tr: { opposition: "Muhalif", independent: "Ana akım / Bağımsız", progov: "İktidara yakın" },
  en: { opposition: "Opposition", independent: "Mainstream / Independent", progov: "Pro-government" },
};

// Shorter versions for bar tooltips and tabs on small screens.
export const GROUP_SHORT = {
  tr: { opposition: "Muhalif", independent: "Ana akım", progov: "İktidara yakın" },
  en: { opposition: "Opposition", independent: "Mainstream", progov: "Pro-gov" },
};

export const TAGS_EN = {
  "#İçPolitika": "#DomesticPolitics", "#DışPolitika": "#ForeignPolicy",
  "#EkonomiVePiyasalar": "#Economy&Markets", "#EnflasyonVeGeçim": "#Inflation&Living",
  "#AdaletVeYargı": "#Justice&Law", "#AnayasaVeMeclis": "#Constitution&Parliament",
  "#SeçimVePartiler": "#Elections&Parties", "#GüvenlikVeTerör": "#Security&Terrorism",
  "#SavunmaSanayii": "#DefenseIndustry", "#GöçVeSığınmacılar": "#Migration&Refugees",
  "#Eğitim": "#Education", "#Sağlık": "#Health", "#KadınVeÇocukHakları": "#Women&ChildrenRights",
  "#İnsanHaklarıVeHukuk": "#HumanRights", "#MedyaVeİfadeÖzgürlüğü": "#Media&FreeSpeech",
  "#YerelYönetimler": "#LocalGov", "#ÇevreVeİklim": "#Environment&Climate",
  "#DepremVeAfet": "#Earthquake&Disaster",
};

export const METHOD = {
  tr: (updated, repoUrl) => `
    <p><b>Gruplar nasıl belirlendi?</b> Her kaynak; sahiplik yapısı ve bağımsız kuruluşların (Reuters Institute Digital News Report,
    Media Bias/Fact Check, Media Ownership Monitor) değerlendirmeleri esas alınarak üç gruptan birine yerleştirilir. Türkiye'de medyadaki
    temel ayrım sol–sağ değil, iktidara yakınlık–muhalefet ekseninde olduğu için gruplar bu eksende tanımlanmıştır.</p>
    <p><b>Kapsam çubukları:</b> Gruplardaki kaynak sayıları farklı olduğu için önce her grubun kendi kaynaklarının yüzde kaçının habere
    yer verdiği hesaplanır, sonra bu oranlar karşılaştırılır.</p>
    <p><b>Kör noktalar:</b> En az 3 kaynağın yer verdiği bir haberde bir grubun payı %10'un altındaysa haber o grubun kör noktası sayılır.
    Hesap RSS beslemelerinde görünen haberlere dayanır; kör nokta, o grubun haberi hiç yapmadığını kesin olarak göstermez.</p>
    <p><b>Gruplama ve özetler:</b> Aynı olayı anlatan haberler Google Gemini ile gruplanır. "Tarafsız Özet"ler yapay zekâ tarafından
    üretilir ve hata içerebilir.</p>
    <p>Sınıflandırmaların son gözden geçirilme tarihi: ${updated}.${repoUrl
      ? ` Hatalı bulduğunuz bir sınıflandırmayı <a href="${repoUrl}/issues" target="_blank" rel="noopener">GitHub üzerinden</a> bildirebilirsiniz.`
      : ""}</p>`,
  en: (updated, repoUrl) => `
    <p><b>How are outlets grouped?</b> Each outlet is placed in one of three groups based on ownership and on assessments by independent
    organisations (Reuters Institute Digital News Report, Media Bias/Fact Check, Media Ownership Monitor). In Turkey the main media divide
    is not left vs. right but proximity to the government vs. opposition, so the groups follow that axis.</p>
    <p><b>Coverage bars:</b> Groups have different numbers of outlets, so we first compute what share of each group's outlets covered a
    story, then compare these shares.</p>
    <p><b>Blindspots:</b> For stories covered by at least 3 outlets, a group's share below 10% marks a blindspot. This is based on what
    appears in RSS feeds; a blindspot does not prove that a group ignored the story entirely.</p>
    <p><b>Clustering &amp; summaries:</b> Stories about the same event are grouped with Google Gemini. "Neutral summaries" are
    AI-generated and may contain errors.</p>
    <p>Classification last reviewed: ${updated}. Explanations below are in Turkish.${repoUrl
      ? ` Spotted a wrong classification? <a href="${repoUrl}/issues" target="_blank" rel="noopener">Open an issue on GitHub</a>.`
      : ""}</p>`,
};
