# Article hashtags in native metadata

Choose relevant tags from the article's actual subject, reader intent and approved brand vocabulary. Preserve valid existing tags on edits. Avoid unrelated trending terms, keyword spam, popularity claims and medical-outcome promises unsupported by the article. Do not invent a fixed count. A platform without a hashtag field may be explicitly not-applicable; a missing required note tag field is a defect.

Record a private article metadata file beside the ContentPackage and reference it through `body_or_asset_refs` / the channel handoff. Retain the exact content hash, destination, native field, proposed tags with their reasons, and existing valid tags to preserve. For note, enter them in its native hashtag field; `#tags` in body prose do not populate that field.

Before saving/publishing, check that the field is populated for the current article. On saved/reopened and public readback, inspect actual native/public tag metadata, record observed tags, exact content hash and evidence, and compare with the plan. Preserve publication permission and target checks. Do not infer tags from body text, a prepared manifest or the fact that a button was clicked. Keep missing/unobserved metadata pending, and do not call the article fully verified until the applicable native/public checks pass.

Use `scripts/check_article_metadata.py METADATA.json --stage prepared|saved|public` as a local completeness check. It catches absent fields, lost valid tags, missing planned tags and non-observations; it neither judges topic relevance nor verifies the supplied evidence remotely. Perform the editorial relevance pass and actual platform inspection separately. No new scheduler, effect or permission is created.

Example shape (synthetic, not a publication receipt):

```json
{
  "platform": "note",
  "content_hash": "exact-reviewed-content-sha256",
  "native_field": "hashtags",
  "planned_tags": [{"tag": "文章の書き方", "reason": "The article teaches how to revise prose"}],
  "prior_valid_tags": [],
  "saved": null,
  "public": null
}
```

For each actually inspected saved/public state, replace null with an observation containing `location` (`native_hashtag_field` / `public_hashtag_metadata`), matching `content_hash`, `tags`, actual `evidence_ref` and `observation_mode: actual`. These fields retain a real observation; do not fill them from the plan or a synthetic example.
