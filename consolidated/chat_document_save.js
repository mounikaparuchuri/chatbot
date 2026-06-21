(function (global) {
        'use strict';

        var DEFAULT_SAVE_WEBHOOK = 'https://n8n.paruchuri.net/webhook/3a2ede5a-1d84-45ff-8610-ea8a914f2fbe';
        var DEFAULT_FETCH_WEBHOOK = 'https://n8n.paruchuri.net/webhook/45f3c8a9-030f-4311-b45d-c6fc605bc0c0';

        function tryParseJsonString(str) {
            if (typeof str !== 'string') return null;
            var trimmed = str.trim();
            if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) return null;
            try { return JSON.parse(trimmed); } catch (_) { return null; }
        }

        function isMetaDocumentKey(key) {
            return /^(summary_message|raw_section|raw_talent_themes_section|user_id|course_id|document_type_id|session_id|id|record_id|created_at|updated_at|status|record|metadata|source|received_at)$/i.test(String(key));
        }

        function isTrivialEmptyContent(val) {
            if (val == null) return true;
            if (typeof val === 'string') {
                var t = val.trim();
                return !t || /^null$/i.test(t) || /^undefined$/i.test(t);
            }
            if (Array.isArray(val)) return val.length === 0;
            if (typeof val === 'object') return Object.keys(val).length === 0;
            return false;
        }

        function hasDisplayableDocumentContent(doc) {
            if (doc == null) return false;
            var summary = formatDocumentSummary(doc, '');
            return !!(summary && summary.trim() && !isTrivialEmptyContent(summary));
        }

        function extractPayloadContent(doc) {
            if (doc == null) return null;
            if (typeof doc === 'string') {
                var parsed = tryParseJsonString(doc);
                if (parsed != null) return extractPayloadContent(parsed);
                if (isTrivialEmptyContent(doc)) return null;
                return doc;
            }
            if (typeof doc !== 'object') return doc;
            if (Array.isArray(doc)) {
                return doc.length === 1 ? extractPayloadContent(doc[0]) : doc;
            }

            if (Object.prototype.hasOwnProperty.call(doc, 'payload') && doc.payload != null) {
                return extractPayloadContent(doc.payload);
            }

            var paths = ['record', 'document', 'data'];
            for (var i = 0; i < paths.length; i++) {
                var node = doc[paths[i]];
                if (node == null) continue;
                if (Array.isArray(node) && node.length) node = node[0];
                if (typeof node !== 'object') continue;
                var extracted = extractPayloadContent(node);
                if (extracted != null && extracted !== doc) return extracted;
            }

            return doc;
        }

        function findPayloadInFetchResponse(raw) {
            if (raw == null) return null;
            if (typeof raw === 'string') {
                var trimmed = raw.trim();
                if (!trimmed) return null;
                var parsed = tryParseJsonString(trimmed);
                return parsed != null ? findPayloadInFetchResponse(parsed) : null;
            }
            if (typeof raw !== 'object') return null;
            if (Array.isArray(raw)) {
                return raw.length ? findPayloadInFetchResponse(raw[0]) : null;
            }

            if (Object.prototype.hasOwnProperty.call(raw, 'payload') && raw.payload != null && raw.payload !== '') {
                var payloadContent = extractPayloadContent(raw.payload);
                if (hasDisplayableDocumentContent(payloadContent)) return payloadContent;
            }

            var paths = ['record', 'document', 'data'];
            for (var i = 0; i < paths.length; i++) {
                var node = raw[paths[i]];
                if (node == null) continue;
                if (Array.isArray(node) && node.length) node = node[0];
                if (typeof node !== 'object') continue;
                var extracted = findPayloadInFetchResponse(node);
                if (hasDisplayableDocumentContent(extracted)) return extracted;
            }

            return null;
        }

        function extractDocumentFromFetchResponse(raw) {
            return findPayloadInFetchResponse(raw);
        }

        function formatDocumentForChatInput(doc, label) {
            if (doc == null) return '';
            label = label || 'Loaded document';
            var readable = formatDocumentSummary(doc, label);
            return readable ? '\n\n' + readable : '';
        }

        function humanizeDocumentKey(key) {
            return String(key).replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
        }

        function formatDocumentValue(val, depth) {
            depth = depth || 0;
            if (val == null || val === '') return '';

            if (typeof val === 'string') {
                var parsed = tryParseJsonString(val);
                if (parsed != null) return formatDocumentValue(parsed, depth);
                return val.trim();
            }

            if (typeof val === 'number' || typeof val === 'boolean') {
                return String(val);
            }

            if (Array.isArray(val)) {
                var items = [];
                for (var i = 0; i < val.length; i++) {
                    var item = val[i];
                    if (item == null || item === '') continue;
                    if (typeof item === 'object') {
                        var nested = formatDocumentValue(item, depth + 1);
                        if (nested) items.push('- ' + nested.replace(/\n/g, '\n  '));
                    } else {
                        items.push('- ' + String(item).trim());
                    }
                }
                return items.join('\n');
            }

            if (typeof val === 'object') {
                var lines = [];
                var keys = Object.keys(val);
                for (var j = 0; j < keys.length; j++) {
                    var k = keys[j];
                    if (isMetaDocumentKey(k)) continue;
                    var v = val[k];
                    if (v == null || v === '') continue;
                    var heading = humanizeDocumentKey(k);
                    if (typeof v === 'object') {
                        var nestedBlock = formatDocumentValue(v, depth + 1);
                        if (!nestedBlock) continue;
                        lines.push('**' + heading + '**');
                        lines.push(nestedBlock);
                        lines.push('');
                    } else {
                        lines.push('**' + heading + ':** ' + String(v).trim());
                    }
                }
                return lines.join('\n').trim();
            }

            return String(val);
        }

        function formatDocumentSummary(doc, label) {
            if (doc == null) return '';
            label = label || 'Retrieved summary';

            if (typeof doc === 'string') {
                var parsedDoc = tryParseJsonString(doc);
                doc = parsedDoc != null ? parsedDoc : doc;
            }

            doc = extractPayloadContent(doc);
            if (doc == null || isTrivialEmptyContent(doc)) return '';

            if (typeof doc === 'string') {
                var trimmedDoc = doc.trim();
                return isTrivialEmptyContent(trimmedDoc) ? '' : trimmedDoc;
            }

            var body = formatDocumentValue(doc, 0);
            return body ? body.trim() : '';
        }

        function gatherWebhookStrings(raw, depth, out) {
            depth = depth || 0;
            out = out || [];
            if (depth > 14 || raw == null) return out;
            if (typeof raw === 'string') {
                var t = raw.trim();
                if (t) out.push(t);
                return out;
            }
            if (Array.isArray(raw)) {
                for (var i = 0; i < raw.length; i++) gatherWebhookStrings(raw[i], depth + 1, out);
                return out;
            }
            if (typeof raw === 'object') {
                var keys = Object.keys(raw);
                for (var j = 0; j < keys.length; j++) gatherWebhookStrings(raw[keys[j]], depth + 1, out);
            }
            return out;
        }

        function normalizeSectionText(text) {
            return text
                .replace(/\*\*/g, '')
                .replace(/__/g, '')
                .replace(/#{1,6}\s+/g, '')
                .replace(/\r\n/g, '\n');
        }

        function hasPhrase(text, phraseRe) {
            if (!text || typeof text !== 'string') return false;
            return phraseRe.test(normalizeSectionText(text));
        }

        function findBestMatchingText(responseText, rawData, phraseRe) {
            var candidates = [];
            if (responseText && typeof responseText === 'string') candidates.push(responseText.trim());
            gatherWebhookStrings(rawData).forEach(function (s) {
                if (hasPhrase(s, phraseRe)) candidates.push(s);
            });
            var best = '';
            for (var i = 0; i < candidates.length; i++) {
                if (candidates[i].length > best.length) best = candidates[i];
            }
            return best || (typeof responseText === 'string' ? responseText.trim() : '');
        }

        function parseSectionAfterPhrase(text, phraseRe) {
            if (!text || typeof text !== 'string') return '';
            var normalized = normalizeSectionText(text);
            var match = phraseRe.exec(normalized);
            if (!match) return normalized.trim();

            var after = normalized.slice(match.index + match[0].length).replace(/^[\s:*\-#]+/, '').trim();
            if (after) return after;
            return normalized.trim();
        }

        function documentFromBulletedSection(block, fullText, listKey) {
            listKey = listKey || 'items';
            var items = [];
            var lines = (block || '').split('\n');
            for (var i = 0; i < lines.length; i++) {
                var line = lines[i].trim();
                if (!line) continue;
                var bullet = line.match(/^\s*(?:\d+[\.\)]\s*|[-*•]\s+)(.+)$/);
                if (bullet) {
                    items.push(bullet[1].trim());
                    continue;
                }
                if (!/^#{1,6}\s/.test(line)) items.push(line);
            }
            var doc = {};
            doc[listKey] = items.length ? items : [block.trim()];
            doc.raw_section = block.trim();
            if (fullText && typeof fullText === 'string') doc.summary_message = fullText.trim();
            return doc;
        }

        function createSectionPhraseTrigger(options) {
            options = options || {};
            var phraseRe = options.phrase instanceof RegExp ? options.phrase : new RegExp(options.phrase, 'i');
            var listKey = options.listKey || 'items';
            var buildDocument = options.buildDocument;

            return {
                detect: function (responseText, rawData) {
                    var text = findBestMatchingText(responseText, rawData, phraseRe);
                    if (!text || !hasPhrase(text, phraseRe)) return null;
                    var block = parseSectionAfterPhrase(text, phraseRe);
                    return {
                        displayMessage: text,
                        document: buildDocument
                            ? buildDocument(text, block)
                            : documentFromBulletedSection(block, text, listKey)
                    };
                }
            };
        }

        function createDocumentSave(config) {
            config = config || {};
            var saveWebhookUrl = config.saveWebhookUrl || DEFAULT_SAVE_WEBHOOK;
            var fetchWebhookUrl = config.fetchWebhookUrl || config.saveWebhookUrl || DEFAULT_FETCH_WEBHOOK;
            var documentTypeId = config.documentTypeId || 'chat_summary';
            var sourceDocumentTypeId = config.sourceDocumentTypeId || null;
            var sourceDocumentLabel = config.sourceDocumentLabel || 'Loaded document';
            var userId = config.userId || '';
            var courseId = config.courseId || '';
            var trigger = config.trigger;
            var cachedSourceDocument = null;
            var sourceDocumentFetched = false;
            var sourceDocumentInjected = false;
            var sourceDocumentSummaryShown = false;

            if (!trigger || typeof trigger.detect !== 'function') {
                throw new Error('ChatDocumentSave.create requires config.trigger with detect()');
            }

            function hasSourceDocumentContent(doc) {
                return hasDisplayableDocumentContent(doc);
            }

            async function fetchSourceDocument() {
                if (!sourceDocumentTypeId) return null;
                if (sourceDocumentFetched) return cachedSourceDocument;
                sourceDocumentFetched = true;
                try {
                    var res = await fetch(fetchWebhookUrl, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            user_id: userId,
                            course_id: courseId,
                            document_type_id: sourceDocumentTypeId
                        })
                    });
                    if (!res.ok) throw new Error('HTTP error! status: ' + res.status);
                    var data = await res.json().catch(function () { return null; });
                    cachedSourceDocument = extractDocumentFromFetchResponse(data);
                    if (!hasSourceDocumentContent(cachedSourceDocument)) {
                        cachedSourceDocument = null;
                    }
                } catch (err) {
                    console.error('Fetch source document error:', err);
                    cachedSourceDocument = null;
                }
                return cachedSourceDocument;
            }

            function appendSourceDocumentFields(payload, chatInput) {
                if (!sourceDocumentTypeId || cachedSourceDocument == null || sourceDocumentInjected) {
                    return chatInput;
                }
                sourceDocumentInjected = true;
                payload.sourceDocumentTypeId = sourceDocumentTypeId;
                payload.sourceDocument = cachedSourceDocument;
                return chatInput + formatDocumentForChatInput(cachedSourceDocument, sourceDocumentLabel);
            }

            async function prepareAgentPayload(basePayload, chatInput) {
                if (sourceDocumentTypeId && !sourceDocumentFetched) {
                    await fetchSourceDocument();
                }
                var mergedInput = appendSourceDocumentFields(basePayload, chatInput || '');
                basePayload.chatInput = mergedInput;
                return basePayload;
            }

            function resetSourceDocumentCache() {
                cachedSourceDocument = null;
                sourceDocumentFetched = false;
                sourceDocumentInjected = false;
                sourceDocumentSummaryShown = false;
            }

            async function saveDocument(documentPayload) {
                if (!documentPayload) return;
                try {
                    var res = await fetch(saveWebhookUrl, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            user_id: userId,
                            course_id: courseId,
                            document_type_id: documentTypeId,
                            document: documentPayload
                        })
                    });
                    if (!res.ok) throw new Error('HTTP error! status: ' + res.status);
                    await res.json().catch(function () { return {}; });
                } catch (err) {
                    console.error('Save error:', err);
                }
            }

            function handleAgentResponse(data, extractReply, addMessage, formatMissing) {
                var responseText = extractReply(data) || '';
                var completion = null;
                try {
                    completion = trigger.detect(responseText, data);
                } catch (err) {
                    console.error('Save trigger detection error:', err);
                }

                if (completion) {
                    addMessage(completion.displayMessage, false);
                    saveDocument(completion.document);
                    return true;
                }

                addMessage(responseText || formatMissing(data), false);
                return false;
            }

            return {
                documentTypeId: documentTypeId,
                sourceDocumentTypeId: sourceDocumentTypeId,
                detectCompletion: function (responseText, rawData) {
                    return trigger.detect(responseText, rawData);
                },
                fetchSourceDocument: fetchSourceDocument,
                getSourceDocument: function () { return cachedSourceDocument; },
                hasSourceDocumentContent: function () { return hasSourceDocumentContent(cachedSourceDocument); },
                hasShownSourceSummary: function () { return sourceDocumentSummaryShown; },
                markSourceSummaryShown: function () { sourceDocumentSummaryShown = true; },
                prepareAgentPayload: prepareAgentPayload,
                resetSourceDocumentCache: resetSourceDocumentCache,
                saveDocument: saveDocument,
                handleAgentResponse: handleAgentResponse
            };
        }

        function resolveDocumentTypeId(pageDefault) {
            var urlParams = new URLSearchParams(global.location && global.location.search || '');
            return urlParams.get('document_type_id')
                || pageDefault
                || (global.PLATFORM_DOC_TYPE)
                || 'chat_summary';
        }

        function resolveSourceDocumentTypeId(pageDefault) {
            var urlParams = new URLSearchParams(global.location && global.location.search || '');
            return urlParams.get('source_document_type_id')
                || urlParams.get('fetch_document_type_id')
                || pageDefault
                || (global.PLATFORM_SOURCE_DOC_TYPE)
                || null;
        }

        function resolveUserContext() {
            var urlParams = new URLSearchParams(global.location && global.location.search || '');
            return {
                userId: urlParams.get('user_id') || global.PLATFORM_USER_ID || '',
                courseId: urlParams.get('course_id') || global.PLATFORM_COURSE_ID || ''
            };
        }

        global.ChatDocumentSave = {
            DEFAULT_SAVE_WEBHOOK: DEFAULT_SAVE_WEBHOOK,
            DEFAULT_FETCH_WEBHOOK: DEFAULT_FETCH_WEBHOOK,
            create: createDocumentSave,
            resolveDocumentTypeId: resolveDocumentTypeId,
            resolveSourceDocumentTypeId: resolveSourceDocumentTypeId,
            resolveUserContext: resolveUserContext,
            formatDocumentForChatInput: formatDocumentForChatInput,
            formatDocumentSummary: formatDocumentSummary,
            extractPayloadContent: extractPayloadContent,
            isTrivialEmptyContent: isTrivialEmptyContent,
            hasDisplayableDocumentContent: hasDisplayableDocumentContent,
            triggers: {
                topTalentThemes: function () {
                    return createSectionPhraseTrigger({
                        phrase: /(?:your\s+)?top\s+\d*\s*talent\s+themes?/i,
                        listKey: 'top_talent_themes'
                    });
                },
                needsAndDesires: function () {
                    return createSectionPhraseTrigger({
                        phrase: /(?:your\s+)?needs\s+(?:and\s+desires)?\s*summary/i,
                        listKey: 'needs_and_desires'
                    });
                },
                sectionPhrase: createSectionPhraseTrigger
            }
        };
    })(typeof window !== 'undefined' ? window : this);
