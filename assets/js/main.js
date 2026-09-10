"use strict";

/* ==========================================================================
   POPPO MAIN.JS
   Static multilingual URL switching + existing website functionality.
   Localized pages are generated at build time; no browser-side DOM translation.
============================================================================= */


/* ==========================================================================
   0. CORE ASSET SAFETY
============================================================================= */

(function ensureCoreStylesheet() {
    const expectedPath = "/assets/css/style.css";
    const expectedHref = new URL(expectedPath, window.location.origin).href;

    const links = Array.from(
        document.querySelectorAll('link[rel~="stylesheet"]')
    );

    let coreLink = links.find((link) => {
        try {
            const url = new URL(
                link.getAttribute("href") || "",
                document.baseURI
            );

            return url.pathname === expectedPath;
        } catch (_) {
            return false;
        }
    });

    if (!coreLink) {
        coreLink = document.createElement("link");
        coreLink.rel = "stylesheet";
        coreLink.href = expectedHref;
        document.head.appendChild(coreLink);
        return;
    }

    try {
        const current = new URL(
            coreLink.getAttribute("href") || "",
            document.baseURI
        );

        if (
            current.pathname !== expectedPath ||
            current.search ||
            current.hash
        ) {
            coreLink.href = expectedHref;
        }
    } catch (_) {
        coreLink.href = expectedHref;
    }
})();


/* ==========================================================================
   1. STATIC MULTILINGUAL URL SYSTEM
   Crawlable locale directories replace browser-side DOM translation.
============================================================================= */

const POPPO_LANGUAGES = Object.freeze({
    en:{label:"English",rtl:false}, tl:{label:"Filipino / Tagalog",rtl:false},
    id:{label:"Bahasa Indonesia",rtl:false}, vi:{label:"Vietnamese",rtl:false},
    th:{label:"Thai",rtl:false}, my:{label:"Burmese",rtl:false}, ms:{label:"Malay",rtl:false},
    km:{label:"Khmer",rtl:false}, lo:{label:"Lao",rtl:false}, hi:{label:"Hindi",rtl:false},
    ur:{label:"Urdu",rtl:true}, bn:{label:"Bangla",rtl:false}, te:{label:"Telugu",rtl:false},
    ta:{label:"Tamil",rtl:false}, pa:{label:"Punjabi",rtl:false}, ne:{label:"Nepali",rtl:false},
    si:{label:"Sinhala",rtl:false}, ar:{label:"Arabic",rtl:true}, tr:{label:"Turkish",rtl:false},
    sw:{label:"Swahili",rtl:false}, am:{label:"Amharic",rtl:false}, fr:{label:"French",rtl:false},
    pt:{label:"Portuguese",rtl:false}, es:{label:"Spanish",rtl:false}, ru:{label:"Russian",rtl:false},
    kk:{label:"Kazakh",rtl:false}, uz:{label:"Uzbek",rtl:false}, uk:{label:"Ukrainian",rtl:false},
    zh:{label:"Chinese",rtl:false}, ja:{label:"Japanese",rtl:false}
});
const POPPO_SUPPORTED_LANGUAGES = Object.keys(POPPO_LANGUAGES);
const POPPO_LANGUAGE_STORAGE_KEY = "preferred_language";

function safeLocalStorageGet(key){try{return localStorage.getItem(key)}catch(_){return null}}
function safeLocalStorageSet(key,value){try{localStorage.setItem(key,value)}catch(_){}}
function currentLocale(){
    const body = document.body && document.body.getAttribute("data-page-locale");
    if (body && POPPO_LANGUAGES[body]) return body;
    const first = location.pathname.split("/").filter(Boolean)[0];
    return POPPO_LANGUAGES[first] && first !== "en" ? first : "en";
}
function originalEnglishPath(){
    const parts=location.pathname.split("/").filter(Boolean);
    if(parts.length && POPPO_LANGUAGES[parts[0]] && parts[0]!=="en") parts.shift();
    let p="/"+parts.join("/");
    if(location.pathname.endsWith("/") && !p.endsWith("/")) p+="/";
    if(p==="/") return p;
    return p || "/";
}
function localizedPath(target){
    const base=originalEnglishPath();
    return target==="en" ? base : "/"+target+(base==="/"?"/":base);
}
function changeLanguage(langCode){
    const target=String(langCode||"").toLowerCase()==="fil"?"tl":String(langCode||"").toLowerCase();
    if(!POPPO_LANGUAGES[target]) return;
    safeLocalStorageSet(POPPO_LANGUAGE_STORAGE_KEY,target);
    const dest=localizedPath(target)+location.search+location.hash;
    if(dest!==location.pathname+location.search+location.hash) location.assign(dest);
}
window.changeLanguage=changeLanguage;
function initializeLanguageUI(){
    document.querySelectorAll("#language-select,[data-language-select]").forEach((select)=>{
        select.value=currentLocale();
        select.addEventListener("change",()=>changeLanguage(select.value));
    });
}
function runtimeI18n(){
    const el=document.getElementById("poppo-i18n-runtime");
    if(!el) return {};
    try{return JSON.parse(el.textContent||"{}").strings||{}}catch(_){return {}}
}
const POPPO_RUNTIME_I18N=runtimeI18n();
function t(source){return POPPO_RUNTIME_I18N[source]||source}

function setupLanguageRecommendation(){
    const box=document.getElementById("language-recommendation");
    if(!box || currentLocale()!=="en") return;
    const raw=(navigator.language||"").toLowerCase();
    let suggested=raw.split("-")[0];
    if(suggested==="fil") suggested="tl";
    if(!POPPO_LANGUAGES[suggested] || suggested==="en") return;
    if(safeLocalStorageGet(POPPO_LANGUAGE_STORAGE_KEY)) return;
    const accept=document.getElementById("language-recommendation-accept");
    const decline=document.getElementById("language-recommendation-decline");
    const close=document.getElementById("language-recommendation-close");
    box.hidden=false;
    if(accept) accept.addEventListener("click",()=>changeLanguage(suggested),{once:true});
    const hide=()=>{box.hidden=true; safeLocalStorageSet(POPPO_LANGUAGE_STORAGE_KEY,"en")};
    if(decline) decline.addEventListener("click",hide,{once:true});
    if(close) close.addEventListener("click",hide,{once:true});
}
document.addEventListener("DOMContentLoaded",()=>{initializeLanguageUI();setupLanguageRecommendation()});

/* ==========================================================================
   3. ORIGINAL UI FUNCTIONS
============================================================================= */

function setupMobileMenu() {
    const menus =
        document.querySelectorAll(
            "details.mobile-menu"
        );

    function closeAll(except) {
        menus.forEach((menu) => {
            if (menu !== except) {
                menu.open = false;
            }
        });
    }

    document.addEventListener(
        "pointerdown",
        (event) => {
            menus.forEach((menu) => {
                if (
                    menu.open &&
                    !menu.contains(event.target)
                ) {
                    menu.open = false;
                }
            });
        }
    );

    document.addEventListener(
        "click",
        (event) => {
            const link =
                event.target.closest &&
                event.target.closest(
                    "details.mobile-menu a"
                );

            if (link) {
                closeAll();
            }
        }
    );

    document.addEventListener(
        "keydown",
        (event) => {
            if (event.key !== "Escape") {
                return;
            }

            closeAll();

            const summary =
                document.querySelector(
                    "details.mobile-menu summary"
                );

            if (summary) {
                summary.focus();
            }
        }
    );

    window.addEventListener(
        "resize",
        () => {
            if (window.innerWidth > 900) {
                closeAll();
            }
        },
        { passive: true }
    );

    menus.forEach((menu) => {
        menu.addEventListener(
            "toggle",
            () => {
                if (menu.open) {
                    closeAll(menu);
                }
            }
        );
    });
}


function setupCopyButtons() {
    const buttons =
        document.querySelectorAll(
            "[data-copy-code], .copy-button"
        );

    buttons.forEach((button) => {
        button.addEventListener(
            "click",
            () => {
                const code =
                    button.getAttribute(
                        "data-copy-code"
                    ) || "73546256";

                const original =
                    button.textContent;

                let copyPromise;

                if (
                    navigator.clipboard &&
                    navigator.clipboard.writeText
                ) {
                    copyPromise =
                        navigator.clipboard.writeText(
                            code
                        );
                } else {
                    copyPromise =
                        Promise.reject(
                            new Error(
                                "Clipboard API unavailable"
                            )
                        );
                }

                copyPromise
                    .catch(() => {
                        const field =
                            document.createElement(
                                "textarea"
                            );

                        field.value = code;
                        field.setAttribute(
                            "readonly",
                            ""
                        );

                        field.style.position =
                            "fixed";

                        field.style.opacity =
                            "0";

                        document.body.appendChild(
                            field
                        );

                        field.select();

                        document.execCommand(
                            "copy"
                        );

                        field.remove();
                    })
                    .finally(() => {
                        button.textContent =
                            t("Copied ✓");

                        window.setTimeout(
                            () => {
                                button.textContent =
                                    original;
                            },
                            2200
                        );
                    });
            }
        );
    });
}


function setupApplicationForm() {
    const form =
        document.getElementById(
            "regForm"
        );

    if (!form) {
        return;
    }

    const status =
        form.querySelector(
            ".form-status"
        );

    const submit =
        form.querySelector(
            "button[type='submit']"
        );

    if (!status || !submit) {
        return;
    }

    function show(kind, message) {
        status.className =
            "form-status " + kind;

        status.textContent =
            message;
    }

    function postJson(url, payload) {
        return fetch(
            url,
            {
                method: "POST",
                headers: {
                    "Content-Type":
                        "application/json"
                },
                body: JSON.stringify(
                    payload
                )
            }
        ).then((response) => {
            return response
                .json()
                .catch(() => {
                    return {
                        success: false,
                        message:
                            t("The server returned an unreadable response.")
                    };
                })
                .then((data) => {
                    if (
                        !response.ok ||
                        !data.success
                    ) {
                        throw new Error(
                            data.message ||
                            t("The application could not be saved.")
                        );
                    }

                    return data;
                });
        });
    }

    form.addEventListener(
        "submit",
        (event) => {
            event.preventDefault();

            const values =
                new FormData(form);

            /*
               Honeypot.
            */
            if (
                String(
                    values.get("website") ||
                    ""
                )
            ) {
                return;
            }

            const payload = {
                full_name:
                    String(
                        values.get(
                            "full_name"
                        ) || ""
                    ).trim(),

                whatsapp:
                    String(
                        values.get(
                            "whatsapp"
                        ) || ""
                    ).trim(),

                email:
                    String(
                        values.get(
                            "email"
                        ) || ""
                    ).trim(),

                city_country:
                    String(
                        values.get(
                            "city_country"
                        ) || ""
                    ).trim(),

                gender:
                    String(
                        values.get(
                            "gender"
                        ) || ""
                    ),

                platform:
                    String(
                        values.get(
                            "platform"
                        ) || ""
                    ),

                talent:
                    String(
                        values.get(
                            "talent"
                        ) || ""
                    ),

                experience:
                    String(
                        values.get(
                            "experience"
                        ) || ""
                    ),

                about_yourself:
                    String(
                        values.get(
                            "about_yourself"
                        ) || ""
                    ).trim()
            };

            if (
                payload.full_name.length < 2
            ) {
                show(
                    "error",
                    t("Enter your full name.")
                );
                return;
            }

            if (
                !/^\+?[\d\s-]{7,20}$/.test(
                    payload.whatsapp
                )
            ) {
                show(
                    "error",
                    t("Enter a valid WhatsApp number with country code.")
                );
                return;
            }

            if (
                !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(
                    payload.email
                )
            ) {
                show(
                    "error",
                    t("Enter a valid email address.")
                );
                return;
            }

            if (
                payload.city_country.length < 2 ||
                !payload.gender ||
                !payload.platform
            ) {
                show(
                    "error",
                    t("Complete every required field.")
                );
                return;
            }

            submit.disabled = true;

            const originalSubmitText =
                submit.textContent;

            submit.textContent =
                t("Submitting…");

            show(
                "loading",
                t("Submitting your application…")
            );

            const base =
                form.getAttribute(
                    "data-api-base"
                ) ||
                "https://www.officialpoppoagency.com";

            postJson(
                base +
                "/api/save_registration.php",
                payload
            )
                .then(() => {
                    postJson(
                        base +
                        "/api/send_email.php",
                        payload
                    ).catch(() => {});

                    form.reset();

                    show(
                        "success",
                        t("Application received. Our team will contact you on WhatsApp after review.")
                    );
                })
                .catch((error) => {
                    show(
                        "error",
                        (
                            error &&
                            error.message
                        ) ||
                        t("Submission failed. Please try again or use WhatsApp.")
                    );
                })
                .finally(() => {
                    submit.disabled = false;
                    submit.textContent =
                        originalSubmitText ||
                        t("Submit application ->");
                });
        }
    );
}


function setupReveal() {
    if (
        !(
            "IntersectionObserver" in window
        ) ||
        window
            .matchMedia(
                "(prefers-reduced-motion: reduce)"
            )
            .matches
    ) {
        return;
    }

    const items =
        document.querySelectorAll(
            ".path-card, " +
            ".feature-card, " +
            ".library-grid > a, " +
            ".guide-section, " +
            ".localized-facts article"
        );

    const observer =
        new IntersectionObserver(
            (entries) => {
                entries.forEach(
                    (entry) => {
                        if (
                            !entry.isIntersecting
                        ) {
                            return;
                        }

                        entry.target.classList.add(
                            "is-visible"
                        );

                        observer.unobserve(
                            entry.target
                        );
                    }
                );
            },
            {
                rootMargin:
                    "0px 0px -8%",
                threshold: 0.08
            }
        );

    items.forEach((item) => {
        item.classList.add(
            "reveal-ready"
        );

        observer.observe(item);
    });
}


/* ==========================================================================
   4. POPPO KNOWLEDGE ASSISTANT
============================================================================= */

const greetings = {
    en:
        "Hi! Ask me anything about Poppo Live, hosting, agencies, coins, withdrawals, safety, or support."
};


const knowledge = [
    {
        words:
            /\b(hi|hello|hey|namaste|hola|bonjour|ola|xin chao|hai)\b/i,

        answer: () =>
            greetings.en
    },

    {
        words:
            /(what is poppo|about poppo|poppo live kya|que es poppo|poppo overview)/i,

        answer:
            "Poppo Live is a live-streaming and social platform operated by VSHOW PTE. LTD. It includes live broadcasts, multi-user rooms, short content, messaging, profiles, and virtual gifts.",

        href: "/",

        label:
            "Read the Poppo Live overview"
    },

    {
        words:
            /(host|streamer|creator|go live|become.*host|live host)/i,

        answer:
            "To become a Poppo host, create a secure account, find your Poppo ID, review the current rules, complete any required verification, and follow the creator or agency onboarding flow. Approval and income are not guaranteed.",

        href: "/host/",

        label:
            "Open the host guide"
    },

    {
        words:
            /(agency code|agent code|code agence|codigo de agencia|agency number)/i,

        answer:
            "Official Poppo Agency's verified agency code is 73546256. Enter it only where the current onboarding flow requests it, and check every digit before submitting.",

        href:
            "/agency-code/",

        label:
            "See how to use the code"
    },

    {
        words:
            /(agency|agent|partner|agence|agencia)/i,

        answer:
            "A Poppo agency is an independent partner that recruits, onboards, supports, and manages creators under current program terms. The agency does not own or operate Poppo Live.",

        href:
            "/agency/",

        label:
            "Open the agency guide"
    },

    {
        words:
            /(download|install|apk|android|iphone|ios|pc|desktop|telecharg|descarg|baixar)/i,

        answer:
            "Download Poppo only from the official Poppo website, Google Play, or Apple App Store. Avoid unknown APK mirrors and desktop installers that request account credentials.",

        href:
            "/download/",

        label:
            "Open safe download options"
    },

    {
        words:
            /(poppo id|account|login|sign in|verify|verification|password|profile|compte|cuenta|conta)/i,

        answer:
            "Your Poppo ID is the numeric identifier shown in your profile. Protect your password and one-time codes, and use Poppo's official in-app support for account restrictions or verification decisions.",

        href:
            "/troubleshooting/",

        label:
            "Open the account guide"
    },

    {
        words:
            /(earn|earning|income|salary|money|commission|guarantee|revenue|ganancia|ganho)/i,

        answer:
            "Poppo does not guarantee income. Results can depend on eligible gifts, activity, engagement, performance, program terms, and compliance. Confirm current rates and rules inside the app before acting.",

        href:
            "/earnings/",

        label:
            "Read the earnings guide"
    },

    {
        words:
            /(coin|gift|virtual gift|coins|cadeau|piece|regalo|moneda|presente|moeda)/i,

        answer:
            "Poppo Coins are paid virtual items used for eligible interactions such as virtual gifts. Purchased coins, creator points, and withdrawable balances are different concepts.",

        href:
            "/coins-recharge/",

        label:
            "Learn about coins and gifts"
    },

    {
        words:
            /(recharge|top up|purchase|payment|recarga|recarregar)/i,

        answer:
            "Recharge through the Poppo app or an official Poppo payment page. Confirm the Poppo ID, amount, currency, and payment method before paying, and keep the receipt.",

        href:
            "/coins-recharge/",

        label:
            "Open the recharge guide"
    },

    {
        words:
            /(withdraw|withdrawal|payout|cash out|pending|retrait|retiro|saque)/i,

        answer:
            "Withdrawal eligibility, methods, thresholds, schedules, currencies, and identity checks can change. Check the current account or program screen, keep transaction evidence, and never pay a third party to release funds.",

        href:
            "/earnings/",

        label:
            "Open the withdrawal guide"
    },

    {
        words:
            /(safe|safety|scam|fraud|otp|password|report|block|ban|restricted|security|seguridad)/i,

        answer:
            "Keep passwords and one-time codes private, use official app and payment sources, and report or block unsafe users inside Poppo. Our agency never needs your password or OTP.",

        href:
            "/rules-safety/",

        label:
            "Open the safety guide"
    },

    {
        words:
            /(rule|policy|allowed|prohibited|content|minor|age requirement|regle|regla|regra)/i,

        answer:
            "Poppo users and hosts must follow current platform terms, live agreements, safety rules, and local law. Check official policy pages because rules and enforcement can change.",

        href:
            "/rules-safety/",

        label:
            "Open the rules guide"
    },

    {
        words:
            /(contact|support|whatsapp|phone|email|human|help|contacter|contacto|contato)/i,

        answer:
            "For Official Poppo Agency onboarding, WhatsApp +91 78383 17307. For account, moderation, recharge, or payout decisions, use Poppo's official in-app support.",

        href:
            "https://wa.me/917838317307",

        label:
            "Message the agency on WhatsApp"
    },

    {
        words:
            /(vone|v one)/i,

        answer:
            "This site does not claim that Poppo Live and Vone are the same product or follow the same rules. Our agency has invitation links for both, but users should verify each app independently.",

        href:
            "/faq/",

        label:
            "Read the Poppo and Vone note"
    },

    {
        words:
            /(problem|not working|error|cannot|issue|trouble|probleme|problema)/i,

        answer:
            "Check the exact in-app notice, update the official app, confirm your connection and permissions, and avoid creating duplicate accounts. Account restrictions and payment decisions must be handled by official Poppo support.",

        href:
            "/troubleshooting/",

        label:
            "Open troubleshooting"
    }
];


function addMessage(
    container,
    role,
    text,
    href,
    label
) {
    const message =
        document.createElement(
            "div"
        );

    message.className =
        "assistant-message " +
        role;

    const paragraph =
        document.createElement(
            "p"
        );

    paragraph.textContent =
        text;

    message.appendChild(
        paragraph
    );

    if (href && label) {
        const link =
            document.createElement(
                "a"
            );

        link.href = href;

        link.textContent =
            label + " ->";

        if (
            /^https?:/i.test(href)
        ) {
            link.target =
                "_blank";

            link.rel =
                "noopener noreferrer";
        }

        message.appendChild(
            link
        );
    }

    container.appendChild(
        message
    );

    container.scrollTop =
        container.scrollHeight;
}


function answerQuestion(
    question,
    locale
) {
    const normalized =
        question
            .toLowerCase()
            .normalize("NFKD")
            .replace(
                /[\u0300-\u036f]/g,
                ""
            );

    for (
        let i = 0;
        i < knowledge.length;
        i += 1
    ) {
        if (
            knowledge[i].words.test(
                normalized
            )
        ) {
            return {
                text:
                    typeof knowledge[i].answer ===
                    "function"
                        ? t(knowledge[i].answer(locale))
                        : t(knowledge[i].answer),

                href:
                    knowledge[i].href,

                label:
                    t(knowledge[i].label)
            };
        }
    }

    return {
        text:
            t("I can answer Poppo questions about downloads, accounts, Poppo ID, hosting, agencies, code 73546256, earnings, coins, recharge, withdrawals, rules, safety, Vone, and support. Ask with one of those topics, or contact our team for personal onboarding help."),

        href:
            "https://wa.me/917838317307",

        label:
            t("Ask the agency on WhatsApp")
    };
}


function setupAssistant() {
    const root =
        document.querySelector(
            "[data-assistant]"
        );

    if (!root) {
        return;
    }

    const panel =
        root.querySelector(
            ".assistant-panel"
        );

    const launcher =
        root.querySelector(
            "[data-assistant-open]"
        );

    const close =
        root.querySelector(
            "[data-assistant-close]"
        );

    const form =
        root.querySelector(
            "#assistant-form"
        );

    const input =
        root.querySelector(
            "#assistant-input"
        );

    const messages =
        root.querySelector(
            "#assistant-messages"
        );

    if (
        !panel ||
        !launcher ||
        !close ||
        !form ||
        !input ||
        !messages
    ) {
        return;
    }

    const locale =
        currentLocale();

    const firstMessage =
        messages.querySelector("p");

    if (firstMessage) {
        firstMessage.textContent =
            t(greetings[locale] || greetings.en);
    }

    function setOpen(open) {
        panel.hidden =
            !open;

        root.classList.toggle(
            "is-open",
            open
        );

        launcher.setAttribute(
            "aria-expanded",
            String(open)
        );

        if (open) {
            window.setTimeout(
                () => {
                    input.focus();
                },
                50
            );
        }
    }

    launcher.addEventListener(
        "click",
        () => {
            setOpen(
                panel.hidden
            );
        }
    );

    close.addEventListener(
        "click",
        () => {
            setOpen(false);
            launcher.focus();
        }
    );

    root
        .querySelectorAll(
            ".assistant-suggestions button"
        )
        .forEach((button) => {
            button.addEventListener(
                "click",
                () => {
                    input.value =
                        button.textContent;

                    if (
                        typeof form.requestSubmit ===
                        "function"
                    ) {
                        form.requestSubmit();
                    } else {
                        form.dispatchEvent(
                            new Event(
                                "submit",
                                {
                                    bubbles: true,
                                    cancelable: true
                                }
                            )
                        );
                    }
                }
            );
        });

    form.addEventListener(
        "submit",
        (event) => {
            event.preventDefault();

            const question =
                input.value.trim();

            if (!question) {
                return;
            }

            addMessage(
                messages,
                "user",
                question
            );

            input.value = "";

            const result =
                answerQuestion(
                    question,
                    currentLocale()
                );

            window.setTimeout(
                () => {
                    addMessage(
                        messages,
                        "assistant",
                        result.text,
                        result.href,
                        result.label
                    );
                },
                220
            );
        }
    );

    document.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key === "Escape" &&
                !panel.hidden
            ) {
                setOpen(false);
            }
        }
    );
}

/* Initialize preserved site behavior. */
function initializePoppoFeatures(){
    setupMobileMenu();
    setupCopyButtons();
    setupApplicationForm();
    setupReveal();
    setupAssistant();
}
if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", initializePoppoFeatures);
else initializePoppoFeatures();
