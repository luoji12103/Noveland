"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  AdminActionBar,
  AdminDescriptionList,
  AdminMetric,
  AdminNotice,
  AdminSection,
  AdminState,
  AdminTable,
} from "@/features/admin/admin-foundation";
import { formString, jsonObject, messageForError, optionalFormString } from "@/features/workspace/form-utils";
import {
  composeScene,
  createSceneBackground,
  createSpriteSet,
  createSpriteVariant,
  deleteSceneBackground,
  deleteSpriteSet,
  deleteSpriteVariant,
  listSceneBackgrounds,
  listSpriteSets,
  listSpriteVariants,
  resolveBackground,
  resolveSprite,
  updateSceneBackground,
  updateSpriteSet,
  updateSpriteVariant,
  visualStatusOptions,
  visualVisibilityOptions,
} from "@/lib/worlds/visual";
import type {
  BackgroundResolveResult,
  SceneBackground,
  SceneComposeResult,
  SpriteResolveResult,
  SpriteSet,
  SpriteVariant,
  VisualRecordStatus,
  VisualVisibility,
} from "@/lib/worlds/visual";
import type { MediaAsset } from "@/lib/worlds/media";
import type { VisualAdminData } from "@/lib/worlds/server";

type VisualAdminProps = {
  worldId: string;
  data: VisualAdminData;
};

export function VisualAdmin({ worldId, data }: VisualAdminProps) {
  const router = useRouter();
  const [notice, setNotice] = useState<string | null>(data.loadError);
  const [isBusy, setIsBusy] = useState(false);
  const [selectedWorldlineId, setSelectedWorldlineId] = useState(data.selectedWorldlineId ?? "");
  const [spriteSets, setSpriteSets] = useState(data.spriteSets);
  const [variantsBySpriteSetId, setVariantsBySpriteSetId] = useState(data.variantsBySpriteSetId);
  const [backgrounds, setBackgrounds] = useState(data.backgrounds);
  const [selectedSpriteSetId, setSelectedSpriteSetId] = useState(data.spriteSets[0]?.id ?? null);
  const [selectedBackgroundId, setSelectedBackgroundId] = useState(data.backgrounds[0]?.id ?? null);
  const [spriteResolveResult, setSpriteResolveResult] = useState<SpriteResolveResult | null>(null);
  const [backgroundResolveResult, setBackgroundResolveResult] =
    useState<BackgroundResolveResult | null>(null);
  const [composeResult, setComposeResult] = useState<SceneComposeResult | null>(null);
  const selectedSpriteSet = useMemo(
    () => spriteSets.find((spriteSet) => spriteSet.id === selectedSpriteSetId) ?? null,
    [spriteSets, selectedSpriteSetId],
  );
  const selectedVariants =
    selectedSpriteSet === null ? [] : variantsBySpriteSetId[selectedSpriteSet.id] ?? [];
  const selectedBackground = useMemo(
    () => backgrounds.find((background) => background.id === selectedBackgroundId) ?? null,
    [backgrounds, selectedBackgroundId],
  );
  const selectableAssets = data.imageAssets.filter(
    (asset) => asset.worldline_id === selectedWorldlineId && asset.status === "available",
  );
  const spriteAssets = selectableAssets.filter((asset) =>
    ["character_sprite", "character_expression", "character_pose", "transparent_png"].includes(
      asset.asset_role,
    ),
  );
  const backgroundAssets = selectableAssets.filter((asset) =>
    ["scene_background", "reference_image", "original_image"].includes(asset.asset_role),
  );
  const restrictedVisualCount =
    spriteSets.filter((item) => restrictedVisibility(item.visibility)).length
    + Object.values(variantsBySpriteSetId)
      .flat()
      .filter((item) => restrictedVisibility(item.visibility)).length
    + backgrounds.filter((item) => restrictedVisibility(item.visibility)).length;

  async function runAction(action: () => Promise<unknown>, success: string) {
    setIsBusy(true);
    setNotice(null);
    try {
      await action();
      setNotice(success);
      router.refresh();
    } catch (error) {
      setNotice(messageForError(error));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleLoadWorldline(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const worldlineId = formString(form, "worldline_id");
    await runAction(async () => {
      const nextSpriteSets = await listSpriteSets(worldId, { worldline_id: worldlineId });
      const nextVariants = await loadVariants(worldId, nextSpriteSets);
      const nextBackgrounds = await listSceneBackgrounds(worldId, { worldline_id: worldlineId });
      setSelectedWorldlineId(worldlineId);
      setSpriteSets(nextSpriteSets);
      setVariantsBySpriteSetId(nextVariants);
      setBackgrounds(nextBackgrounds);
      setSelectedSpriteSetId(nextSpriteSets[0]?.id ?? null);
      setSelectedBackgroundId(nextBackgrounds[0]?.id ?? null);
      setSpriteResolveResult(null);
      setBackgroundResolveResult(null);
      setComposeResult(null);
    }, "Visual records loaded for worldline.");
  }

  async function handleCreateSpriteSet(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(async () => {
      const spriteSet = await createSpriteSet(worldId, {
        worldline_id: formString(form, "worldline_id"),
        agent_id: formString(form, "agent_id"),
        style_key: formString(form, "style_key"),
        display_name: formString(form, "display_name"),
        default_variant_id: optionalFormString(form, "default_variant_id"),
        status: formString(form, "status") as VisualRecordStatus,
        visibility: formString(form, "visibility") as VisualVisibility,
        metadata_json: sanitizeJsonForDisplay(jsonObject(formString(form, "metadata_json"))),
      });
      setSelectedSpriteSetId(spriteSet.id);
      formElement.reset();
    }, "Sprite set created.");
  }

  async function handleUpdateSpriteSet(event: FormEvent<HTMLFormElement>, spriteSetId: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateSpriteSet(worldId, spriteSetId, {
          display_name: formString(form, "display_name"),
          default_variant_id: optionalFormString(form, "default_variant_id"),
          status: formString(form, "status") as VisualRecordStatus,
          visibility: formString(form, "visibility") as VisualVisibility,
          metadata_json: sanitizeJsonForDisplay(jsonObject(formString(form, "metadata_json"))),
        }),
      "Sprite set saved.",
    );
  }

  async function handleCreateVariant(event: FormEvent<HTMLFormElement>, spriteSetId: string) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(async () => {
      await createSpriteVariant(worldId, spriteSetId, {
        worldline_id: formString(form, "worldline_id"),
        asset_id: formString(form, "asset_id"),
        expression_key: formString(form, "expression_key"),
        pose_key: optionalFormString(form, "pose_key"),
        outfit_key: optionalFormString(form, "outfit_key"),
        mood_tags: csvList(formString(form, "mood_tags")),
        priority: numberField(form, "priority", 100),
        is_default: checkbox(form, "is_default"),
        status: formString(form, "status") as VisualRecordStatus,
        visibility: formString(form, "visibility") as VisualVisibility,
        metadata_json: sanitizeJsonForDisplay(jsonObject(formString(form, "metadata_json"))),
      });
      formElement.reset();
    }, "Sprite variant created.");
  }

  async function handleUpdateVariant(
    event: FormEvent<HTMLFormElement>,
    spriteSetId: string,
    variantId: string,
  ) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateSpriteVariant(worldId, spriteSetId, variantId, {
          asset_id: formString(form, "asset_id"),
          expression_key: formString(form, "expression_key"),
          pose_key: optionalFormString(form, "pose_key"),
          outfit_key: optionalFormString(form, "outfit_key"),
          mood_tags: csvList(formString(form, "mood_tags")),
          priority: numberField(form, "priority", 100),
          is_default: checkbox(form, "is_default"),
          status: formString(form, "status") as VisualRecordStatus,
          visibility: formString(form, "visibility") as VisualVisibility,
          metadata_json: sanitizeJsonForDisplay(jsonObject(formString(form, "metadata_json"))),
        }),
      "Sprite variant saved.",
    );
  }

  async function handleCreateBackground(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    await runAction(async () => {
      const background = await createSceneBackground(worldId, {
        worldline_id: formString(form, "worldline_id"),
        scene_id: optionalFormString(form, "scene_id"),
        location_key: formString(form, "location_key"),
        time_of_day: optionalFormString(form, "time_of_day"),
        weather_key: optionalFormString(form, "weather_key"),
        asset_id: formString(form, "asset_id"),
        priority: numberField(form, "priority", 100),
        is_default: checkbox(form, "is_default"),
        status: formString(form, "status") as VisualRecordStatus,
        visibility: formString(form, "visibility") as VisualVisibility,
        metadata_json: sanitizeJsonForDisplay(jsonObject(formString(form, "metadata_json"))),
      });
      setSelectedBackgroundId(background.id);
      formElement.reset();
    }, "Scene background created.");
  }

  async function handleUpdateBackground(event: FormEvent<HTMLFormElement>, backgroundId: string) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(
      () =>
        updateSceneBackground(worldId, backgroundId, {
          scene_id: optionalFormString(form, "scene_id"),
          location_key: formString(form, "location_key"),
          time_of_day: optionalFormString(form, "time_of_day"),
          weather_key: optionalFormString(form, "weather_key"),
          asset_id: formString(form, "asset_id"),
          priority: numberField(form, "priority", 100),
          is_default: checkbox(form, "is_default"),
          status: formString(form, "status") as VisualRecordStatus,
          visibility: formString(form, "visibility") as VisualVisibility,
          metadata_json: sanitizeJsonForDisplay(jsonObject(formString(form, "metadata_json"))),
        }),
      "Scene background saved.",
    );
  }

  async function handleResolveSprite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setSpriteResolveResult(
        await resolveSprite(worldId, {
          worldline_id: formString(form, "worldline_id"),
          agent_id: formString(form, "agent_id"),
          expression_key: optionalFormString(form, "expression_key"),
          pose_key: optionalFormString(form, "pose_key"),
          outfit_key: optionalFormString(form, "outfit_key"),
          mood_tags: csvList(formString(form, "mood_tags")),
          style_key: optionalFormString(form, "style_key"),
          include_restricted: checkbox(form, "include_restricted"),
        }),
      );
    }, "Sprite resolver completed.");
  }

  async function handleResolveBackground(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setBackgroundResolveResult(
        await resolveBackground(worldId, {
          worldline_id: formString(form, "worldline_id"),
          scene_id: optionalFormString(form, "scene_id"),
          location_key: formString(form, "location_key"),
          time_of_day: optionalFormString(form, "time_of_day"),
          weather_key: optionalFormString(form, "weather_key"),
          include_restricted: checkbox(form, "include_restricted"),
        }),
      );
    }, "Background resolver completed.");
  }

  async function handleComposeScene(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await runAction(async () => {
      setComposeResult(
        await composeScene(worldId, {
          worldline_id: formString(form, "worldline_id"),
          background_asset_id: formString(form, "background_asset_id"),
          layers: sceneLayers(jsonObject(formString(form, "layers_json"))),
          metadata_json: sanitizeJsonForDisplay(jsonObject(formString(form, "metadata_json"))),
        }),
      );
    }, "Scene composition completed.");
  }

  return (
    <section className="management-section">
      {notice !== null ? <AdminNotice>{notice}</AdminNotice> : null}

      {!data.canManageSelectedWorld ? (
        <AdminNotice tone="error">Visual administration requires world admin access.</AdminNotice>
      ) : null}

      <AdminSection
        title="Visual asset overview"
        description="Strict-worldline sprite and background bindings. Media bytes stay in the media kernel."
      >
        <div className="dashboard-grid">
          <AdminMetric label="Sprite sets" value={spriteSets.length} />
          <AdminMetric label="Variants" value={Object.values(variantsBySpriteSetId).flat().length} />
          <AdminMetric label="Backgrounds" value={backgrounds.length} />
          <AdminMetric label="Image assets" value={selectableAssets.length} />
          <AdminMetric
            label="Restricted"
            value={restrictedVisualCount}
            tone={restrictedVisualCount > 0 ? "warning" : "neutral"}
          />
        </div>
      </AdminSection>

      <AdminSection
        title="Worldline scope"
        description="Visual bindings are never global defaults. Select one concrete worldline before managing records."
      >
        {data.worldlines.length === 0 ? (
          <AdminState title="No worldlines">Create or load a worldline before adding visual bindings.</AdminState>
        ) : (
          <form className="inline-form" onSubmit={handleLoadWorldline}>
            <select
              className="text-input"
              name="worldline_id"
              value={selectedWorldlineId}
              onChange={(event) => setSelectedWorldlineId(event.target.value)}
            >
              {data.worldlines.map((worldline) => (
                <option key={worldline.id} value={worldline.id}>
                  {worldline.name} ({worldline.worldline_key})
                </option>
              ))}
            </select>
            <button className="secondary-button" type="submit" disabled={isBusy}>
              Load visual records
            </button>
          </form>
        )}
      </AdminSection>

      <AdminSection
        title="Create sprite set"
        description="Bind one character/agent to a visual style in the selected worldline."
      >
        <form className="management-form" onSubmit={handleCreateSpriteSet}>
          <HiddenWorldlineInput value={selectedWorldlineId} />
          <select className="text-input" name="agent_id" defaultValue={data.agents[0]?.id ?? ""}>
            {data.agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.display_name} ({agent.agent_key})
              </option>
            ))}
          </select>
          <input className="text-input" name="style_key" placeholder="style key" defaultValue="default" />
          <input className="text-input" name="display_name" placeholder="Display name" />
          <select className="text-input" name="status" defaultValue="active">
            {visualStatusOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <VisibilitySelect isPlatformAdmin={data.isPlatformAdmin} />
          <textarea className="text-input" name="metadata_json" defaultValue="{}" rows={3} />
          <button className="primary-button" type="submit" disabled={isBusy || !canSubmit(data, selectedWorldlineId)}>
            Create sprite set
          </button>
        </form>
      </AdminSection>

      <AdminSection title="Sprite sets">
        <div className="resource-list">
          {spriteSets.length === 0 ? (
            <AdminState title="No sprite sets">
              Create a strict-worldline sprite set, then add variants that point to image media assets.
            </AdminState>
          ) : (
            spriteSets.map((spriteSet) => (
              <SpriteSetRow
                key={spriteSet.id}
                spriteSet={spriteSet}
                agentName={agentLabel(data, spriteSet.agent_id)}
                variantCount={variantsBySpriteSetId[spriteSet.id]?.length ?? 0}
                isSelected={spriteSet.id === selectedSpriteSetId}
                onSelect={() => setSelectedSpriteSetId(spriteSet.id)}
              />
            ))
          )}
        </div>
      </AdminSection>

      {selectedSpriteSet === null ? null : (
        <SpriteSetDetail
          spriteSet={selectedSpriteSet}
          variants={selectedVariants}
          spriteAssets={spriteAssets}
          isBusy={isBusy}
          isPlatformAdmin={data.isPlatformAdmin}
          onUpdate={(event) => handleUpdateSpriteSet(event, selectedSpriteSet.id)}
          onDelete={() =>
            runAction(() => deleteSpriteSet(worldId, selectedSpriteSet.id), "Sprite set deleted.")
          }
          onCreateVariant={(event) => handleCreateVariant(event, selectedSpriteSet.id)}
          onUpdateVariant={(event, variantId) =>
            handleUpdateVariant(event, selectedSpriteSet.id, variantId)
          }
          onDeleteVariant={(variantId) =>
            runAction(
              () => deleteSpriteVariant(worldId, selectedSpriteSet.id, variantId),
              "Sprite variant deleted.",
            )
          }
        />
      )}

      <AdminSection
        title="Create scene background"
        description="Register a scene/location background binding in the selected worldline."
      >
        <form className="management-form" onSubmit={handleCreateBackground}>
          <HiddenWorldlineInput value={selectedWorldlineId} />
          <select className="text-input" name="scene_id" defaultValue="">
            <option value="">scene optional</option>
            {data.scenes.map((scene) => (
              <option key={scene.id} value={scene.id}>
                {scene.name} ({scene.scene_key})
              </option>
            ))}
          </select>
          <input className="text-input" name="location_key" placeholder="location key" />
          <input className="text-input" name="time_of_day" placeholder="time of day" />
          <input className="text-input" name="weather_key" placeholder="weather" />
          <AssetSelect assets={backgroundAssets} name="asset_id" fallbackLabel="background asset id" />
          <input className="text-input" name="priority" type="number" defaultValue="100" min="0" />
          <label className="checkbox-row">
            <input name="is_default" type="checkbox" /> default
          </label>
          <select className="text-input" name="status" defaultValue="active">
            {visualStatusOptions.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <VisibilitySelect isPlatformAdmin={data.isPlatformAdmin} />
          <textarea className="text-input" name="metadata_json" defaultValue="{}" rows={3} />
          <button className="primary-button" type="submit" disabled={isBusy || !canSubmit(data, selectedWorldlineId)}>
            Create background
          </button>
        </form>
      </AdminSection>

      <AdminSection title="Scene backgrounds">
        <AdminTable
          caption="Scene backgrounds"
          rows={backgrounds}
          getRowKey={(background) => background.id}
          columns={[
            { key: "location", header: "Location", render: (background) => background.location_key },
            { key: "scene", header: "Scene", render: (background) => sceneLabel(data, background.scene_id) },
            { key: "context", header: "Context", render: (background) => backgroundContext(background) },
            { key: "asset", header: "Asset", render: (background) => assetLabel(data.imageAssets, background.asset_id) },
            { key: "state", header: "State", render: (background) => `${background.status} / ${background.visibility}` },
            {
              key: "action",
              header: "Action",
              render: (background) => (
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setSelectedBackgroundId(background.id)}
                >
                  {background.id === selectedBackgroundId ? "Selected" : "Inspect"}
                </button>
              ),
            },
          ]}
          emptyTitle="No scene backgrounds"
          emptyMessage="Create a background profile for a scene or location in the selected worldline."
        />
      </AdminSection>

      {selectedBackground === null ? null : (
        <BackgroundDetail
          background={selectedBackground}
          scenes={data.scenes}
          assets={backgroundAssets}
          isBusy={isBusy}
          isPlatformAdmin={data.isPlatformAdmin}
          onUpdate={(event) => handleUpdateBackground(event, selectedBackground.id)}
          onDelete={() =>
            runAction(
              () => deleteSceneBackground(worldId, selectedBackground.id),
              "Scene background deleted.",
            )
          }
        />
      )}

      <AdminSection
        title="Resolver previews"
        description="Resolver calls are explicit admin checks. They return selected asset IDs and fallback reasons, not storage paths."
      >
        <div className="split-grid">
          <form className="management-form" onSubmit={handleResolveSprite}>
            <HiddenWorldlineInput value={selectedWorldlineId} />
            <select className="text-input" name="agent_id" defaultValue={selectedSpriteSet?.agent_id ?? data.agents[0]?.id ?? ""}>
              {data.agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.display_name} ({agent.agent_key})
                </option>
              ))}
            </select>
            <input className="text-input" name="expression_key" placeholder="expression" defaultValue="neutral" />
            <input className="text-input" name="pose_key" placeholder="pose" />
            <input className="text-input" name="outfit_key" placeholder="outfit" />
            <input className="text-input" name="style_key" placeholder="style key" />
            <input className="text-input" name="mood_tags" placeholder="mood tags" />
            <RestrictedCheckbox isPlatformAdmin={data.isPlatformAdmin} />
            <button className="secondary-button" type="submit" disabled={isBusy || !canSubmit(data, selectedWorldlineId)}>
              Resolve sprite
            </button>
          </form>
          <form className="management-form" onSubmit={handleResolveBackground}>
            <HiddenWorldlineInput value={selectedWorldlineId} />
            <select className="text-input" name="scene_id" defaultValue={selectedBackground?.scene_id ?? ""}>
              <option value="">scene optional</option>
              {data.scenes.map((scene) => (
                <option key={scene.id} value={scene.id}>
                  {scene.name} ({scene.scene_key})
                </option>
              ))}
            </select>
            <input
              className="text-input"
              name="location_key"
              placeholder="location key"
              defaultValue={selectedBackground?.location_key ?? ""}
            />
            <input className="text-input" name="time_of_day" placeholder="time of day" />
            <input className="text-input" name="weather_key" placeholder="weather" />
            <RestrictedCheckbox isPlatformAdmin={data.isPlatformAdmin} />
            <button className="secondary-button" type="submit" disabled={isBusy || !canSubmit(data, selectedWorldlineId)}>
              Resolve background
            </button>
          </form>
        </div>
        <ResolverResults sprite={spriteResolveResult} background={backgroundResolveResult} />
      </AdminSection>

      <AdminSection
        title="Compose scene"
        description="Explicit composition reuses the existing visual compose endpoint and writes a media job/output asset."
      >
        <form className="management-form" onSubmit={handleComposeScene}>
          <HiddenWorldlineInput value={selectedWorldlineId} />
          <AssetSelect assets={backgroundAssets} name="background_asset_id" fallbackLabel="background asset id" />
          <textarea
            className="text-input"
            name="layers_json"
            rows={4}
            defaultValue={JSON.stringify(defaultLayers(spriteAssets), null, 2)}
          />
          <textarea className="text-input" name="metadata_json" defaultValue="{}" rows={3} />
          <button className="primary-button" type="submit" disabled={isBusy || !canSubmit(data, selectedWorldlineId)}>
            Compose scene
          </button>
        </form>
        {composeResult === null ? null : (
          <AdminDescriptionList
            items={[
              { label: "Output asset", value: composeResult.output_asset.id },
              { label: "Worldline", value: composeResult.output_asset.worldline_id },
              { label: "Job status", value: composeResult.media_job.status },
              { label: "Checksum", value: composeResult.output_asset.checksum_sha256 ?? "pending" },
              { label: "Objects", value: composeResult.output_objects.length },
            ]}
          />
        )}
      </AdminSection>
    </section>
  );
}

function SpriteSetRow({
  spriteSet,
  agentName,
  variantCount,
  isSelected,
  onSelect,
}: {
  spriteSet: SpriteSet;
  agentName: string;
  variantCount: number;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <article className="resource-row" data-selected={isSelected ? "true" : "false"}>
      <div>
        <h3>{spriteSet.display_name}</h3>
        <p>
          {agentName} - {spriteSet.style_key} - {spriteSet.status} - {spriteSet.visibility}
        </p>
        <p>
          Worldline {shortId(spriteSet.worldline_id)} / variants {variantCount} / default{" "}
          {spriteSet.default_variant_id === null ? "missing" : shortId(spriteSet.default_variant_id)}
        </p>
      </div>
      <button className="secondary-button" type="button" onClick={onSelect}>
        {isSelected ? "Selected" : "Inspect"}
      </button>
    </article>
  );
}

function SpriteSetDetail({
  spriteSet,
  variants,
  spriteAssets,
  isBusy,
  isPlatformAdmin,
  onUpdate,
  onDelete,
  onCreateVariant,
  onUpdateVariant,
  onDeleteVariant,
}: {
  spriteSet: SpriteSet;
  variants: SpriteVariant[];
  spriteAssets: MediaAsset[];
  isBusy: boolean;
  isPlatformAdmin: boolean;
  onUpdate: (event: FormEvent<HTMLFormElement>) => void;
  onDelete: () => void;
  onCreateVariant: (event: FormEvent<HTMLFormElement>) => void;
  onUpdateVariant: (event: FormEvent<HTMLFormElement>, variantId: string) => void;
  onDeleteVariant: (variantId: string) => void;
}) {
  return (
    <AdminSection
      title="Sprite set detail"
      description="Variants must point to same-worldline image media assets. Hidden variants are backend-filtered."
      actions={
        <button className="secondary-button" type="button" disabled={isBusy} onClick={onDelete}>
          Delete sprite set
        </button>
      }
    >
      <AdminDescriptionList
        items={[
          { label: "Sprite set", value: spriteSet.id },
          { label: "Worldline", value: spriteSet.worldline_id },
          { label: "Agent", value: spriteSet.agent_id },
          { label: "Style", value: spriteSet.style_key },
          { label: "Default variant", value: spriteSet.default_variant_id ?? "missing" },
          { label: "Metadata keys", value: safeJsonSummary(spriteSet.metadata_json) },
        ]}
      />
      {restrictedVisibility(spriteSet.visibility) ? (
        <AdminNotice tone="warning">
          This sprite set uses restricted visibility. Backend ACLs decide whether it is returned.
        </AdminNotice>
      ) : null}
      <form className="inline-form" onSubmit={onUpdate}>
        <input className="text-input" name="display_name" defaultValue={spriteSet.display_name} />
        <select className="text-input" name="default_variant_id" defaultValue={spriteSet.default_variant_id ?? ""}>
          <option value="">no default</option>
          {variants.map((variant) => (
            <option key={variant.id} value={variant.id}>
              {variant.expression_key} ({shortId(variant.id)})
            </option>
          ))}
        </select>
        <select className="text-input" name="status" defaultValue={spriteSet.status}>
          {visualStatusOptions.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <VisibilitySelect isPlatformAdmin={isPlatformAdmin} defaultValue={spriteSet.visibility} />
        <textarea
          className="text-input"
          name="metadata_json"
          rows={3}
          defaultValue={JSON.stringify(sanitizeJsonForDisplay(spriteSet.metadata_json), null, 2)}
        />
        <button className="primary-button" type="submit" disabled={isBusy}>
          Save sprite set
        </button>
      </form>

      <form className="management-form" onSubmit={onCreateVariant}>
        <HiddenWorldlineInput value={spriteSet.worldline_id} />
        <AssetSelect assets={spriteAssets} name="asset_id" fallbackLabel="sprite asset id" />
        <input className="text-input" name="expression_key" defaultValue="neutral" />
        <input className="text-input" name="pose_key" placeholder="pose" />
        <input className="text-input" name="outfit_key" placeholder="outfit" />
        <input className="text-input" name="mood_tags" placeholder="mood tags" />
        <input className="text-input" name="priority" type="number" defaultValue="100" min="0" />
        <label className="checkbox-row">
          <input name="is_default" type="checkbox" /> default
        </label>
        <select className="text-input" name="status" defaultValue="active">
          {visualStatusOptions.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <VisibilitySelect isPlatformAdmin={isPlatformAdmin} />
        <textarea className="text-input" name="metadata_json" defaultValue="{}" rows={3} />
        <button className="secondary-button" type="submit" disabled={isBusy}>
          Add variant
        </button>
      </form>

      <AdminTable
        caption="Sprite variants"
        rows={variants}
        getRowKey={(variant) => variant.id}
        columns={[
          { key: "expression", header: "Expression", render: (variant) => variant.expression_key },
          { key: "pose", header: "Pose", render: (variant) => variant.pose_key ?? "-" },
          { key: "outfit", header: "Outfit", render: (variant) => variant.outfit_key ?? "-" },
          { key: "asset", header: "Asset", render: (variant) => assetLabel(spriteAssets, variant.asset_id) },
          { key: "state", header: "State", render: (variant) => `${variant.status} / ${variant.visibility}` },
          {
            key: "actions",
            header: "Actions",
            render: (variant) => (
              <VariantActions
                variant={variant}
                spriteAssets={spriteAssets}
                isBusy={isBusy}
                isPlatformAdmin={isPlatformAdmin}
                onUpdate={(event) => onUpdateVariant(event, variant.id)}
                onDelete={() => onDeleteVariant(variant.id)}
              />
            ),
          },
        ]}
        emptyTitle="No sprite variants"
        emptyMessage="Add neutral/default variants first so resolver fallback stays deterministic."
      />
    </AdminSection>
  );
}

function VariantActions({
  variant,
  spriteAssets,
  isBusy,
  isPlatformAdmin,
  onUpdate,
  onDelete,
}: {
  variant: SpriteVariant;
  spriteAssets: MediaAsset[];
  isBusy: boolean;
  isPlatformAdmin: boolean;
  onUpdate: (event: FormEvent<HTMLFormElement>) => void;
  onDelete: () => void;
}) {
  return (
    <form className="inline-form" onSubmit={onUpdate}>
      <AssetSelect assets={spriteAssets} name="asset_id" fallbackLabel="sprite asset id" defaultValue={variant.asset_id} />
      <input className="text-input" name="expression_key" defaultValue={variant.expression_key} />
      <input className="text-input" name="pose_key" defaultValue={variant.pose_key ?? ""} placeholder="pose" />
      <input className="text-input" name="outfit_key" defaultValue={variant.outfit_key ?? ""} placeholder="outfit" />
      <input className="text-input" name="mood_tags" defaultValue={variant.mood_tags.join(", ")} placeholder="mood tags" />
      <input className="text-input" name="priority" type="number" defaultValue={variant.priority} min="0" />
      <label className="checkbox-row">
        <input name="is_default" type="checkbox" defaultChecked={variant.is_default} /> default
      </label>
      <select className="text-input" name="status" defaultValue={variant.status}>
        {visualStatusOptions.map((value) => (
          <option key={value} value={value}>
            {value}
          </option>
        ))}
      </select>
      <VisibilitySelect isPlatformAdmin={isPlatformAdmin} defaultValue={variant.visibility} />
      <textarea
        className="text-input"
        name="metadata_json"
        rows={2}
        defaultValue={JSON.stringify(sanitizeJsonForDisplay(variant.metadata_json), null, 2)}
      />
      <AdminActionBar>
        <button className="secondary-button" type="submit" disabled={isBusy}>
          Save variant
        </button>
        <button className="secondary-button" type="button" disabled={isBusy} onClick={onDelete}>
          Delete
        </button>
      </AdminActionBar>
    </form>
  );
}

function BackgroundDetail({
  background,
  scenes,
  assets,
  isBusy,
  isPlatformAdmin,
  onUpdate,
  onDelete,
}: {
  background: SceneBackground;
  scenes: VisualAdminData["scenes"];
  assets: MediaAsset[];
  isBusy: boolean;
  isPlatformAdmin: boolean;
  onUpdate: (event: FormEvent<HTMLFormElement>) => void;
  onDelete: () => void;
}) {
  return (
    <AdminSection
      title="Background detail"
      description="Background records bind scenes and locations to existing image media assets."
      actions={
        <button className="secondary-button" type="button" disabled={isBusy} onClick={onDelete}>
          Delete background
        </button>
      }
    >
      <AdminDescriptionList
        items={[
          { label: "Background", value: background.id },
          { label: "Worldline", value: background.worldline_id },
          { label: "Scene", value: background.scene_id ?? "location-only" },
          { label: "Asset", value: background.asset_id },
          { label: "Metadata keys", value: safeJsonSummary(background.metadata_json) },
        ]}
      />
      <form className="inline-form" onSubmit={onUpdate}>
        <select className="text-input" name="scene_id" defaultValue={background.scene_id ?? ""}>
          <option value="">scene optional</option>
          {scenes.map((scene) => (
            <option key={scene.id} value={scene.id}>
              {scene.name} ({scene.scene_key})
            </option>
          ))}
        </select>
        <input className="text-input" name="location_key" defaultValue={background.location_key} />
        <input className="text-input" name="time_of_day" defaultValue={background.time_of_day ?? ""} />
        <input className="text-input" name="weather_key" defaultValue={background.weather_key ?? ""} />
        <AssetSelect assets={assets} name="asset_id" fallbackLabel="background asset id" defaultValue={background.asset_id} />
        <input className="text-input" name="priority" type="number" defaultValue={background.priority} min="0" />
        <label className="checkbox-row">
          <input name="is_default" type="checkbox" defaultChecked={background.is_default} /> default
        </label>
        <select className="text-input" name="status" defaultValue={background.status}>
          {visualStatusOptions.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <VisibilitySelect isPlatformAdmin={isPlatformAdmin} defaultValue={background.visibility} />
        <textarea
          className="text-input"
          name="metadata_json"
          rows={3}
          defaultValue={JSON.stringify(sanitizeJsonForDisplay(background.metadata_json), null, 2)}
        />
        <button className="primary-button" type="submit" disabled={isBusy}>
          Save background
        </button>
      </form>
    </AdminSection>
  );
}

function ResolverResults({
  sprite,
  background,
}: {
  sprite: SpriteResolveResult | null;
  background: BackgroundResolveResult | null;
}) {
  if (sprite === null && background === null) {
    return null;
  }
  return (
    <div className="split-grid">
      {sprite === null ? null : (
        <AdminDescriptionList
          items={[
            { label: "Sprite asset", value: sprite.asset.id },
            { label: "Expression", value: sprite.variant.expression_key },
            { label: "Pose", value: sprite.variant.pose_key ?? "-" },
            { label: "Fallback", value: sprite.fallback_reason ?? "exact" },
            { label: "Confidence", value: sprite.confidence.toFixed(2) },
          ]}
        />
      )}
      {background === null ? null : (
        <AdminDescriptionList
          items={[
            { label: "Background asset", value: background.asset.id },
            { label: "Location", value: background.background.location_key },
            { label: "Fallback", value: background.fallback_reason ?? "exact" },
            { label: "Confidence", value: background.confidence.toFixed(2) },
          ]}
        />
      )}
    </div>
  );
}

function VisibilitySelect({
  isPlatformAdmin,
  defaultValue = "world_admin",
}: {
  isPlatformAdmin: boolean;
  defaultValue?: VisualVisibility;
}) {
  const options = isPlatformAdmin
    ? visualVisibilityOptions
    : visualVisibilityOptions.filter((value) => !restrictedVisibility(value));
  return (
    <select className="text-input" name="visibility" defaultValue={defaultValue}>
      {options.map((value) => (
        <option key={value} value={value}>
          {value}
        </option>
      ))}
    </select>
  );
}

function RestrictedCheckbox({ isPlatformAdmin }: { isPlatformAdmin: boolean }) {
  return (
    <label className="checkbox-row">
      <input name="include_restricted" type="checkbox" disabled={!isPlatformAdmin} /> include restricted
    </label>
  );
}

function AssetSelect({
  assets,
  name,
  fallbackLabel,
  defaultValue,
}: {
  assets: MediaAsset[];
  name: string;
  fallbackLabel: string;
  defaultValue?: string;
}) {
  if (assets.length === 0) {
    return <input className="text-input" name={name} placeholder={fallbackLabel} defaultValue={defaultValue ?? ""} />;
  }
  return (
    <select className="text-input" name={name} defaultValue={defaultValue ?? assets[0].id}>
      {assets.map((asset) => (
        <option key={asset.id} value={asset.id}>
          {asset.title ?? asset.asset_role} ({shortId(asset.id)})
        </option>
      ))}
    </select>
  );
}

function HiddenWorldlineInput({ value }: { value: string }) {
  return <input name="worldline_id" type="hidden" value={value} readOnly />;
}

async function loadVariants(worldId: string, spriteSets: SpriteSet[]) {
  const entries = await Promise.all(
    spriteSets.map(async (spriteSet) => [
      spriteSet.id,
      await listSpriteVariants(worldId, spriteSet.id),
    ] as const),
  );
  return Object.fromEntries(entries);
}

function canSubmit(data: VisualAdminData, selectedWorldlineId: string): boolean {
  return data.canManageSelectedWorld && selectedWorldlineId !== "";
}

function agentLabel(data: VisualAdminData, agentId: string): string {
  const agent = data.agents.find((item) => item.id === agentId);
  return agent === undefined ? shortId(agentId) : `${agent.display_name} (${agent.agent_key})`;
}

function sceneLabel(data: VisualAdminData, sceneId: string | null): string {
  if (sceneId === null) {
    return "location-only";
  }
  const scene = data.scenes.find((item) => item.id === sceneId);
  return scene === undefined ? shortId(sceneId) : `${scene.name} (${scene.scene_key})`;
}

function assetLabel(assets: MediaAsset[], assetId: string): string {
  const asset = assets.find((item) => item.id === assetId);
  return asset === undefined ? shortId(assetId) : `${asset.title ?? asset.asset_role} (${shortId(asset.id)})`;
}

function backgroundContext(background: SceneBackground): string {
  return [background.time_of_day, background.weather_key].filter(Boolean).join(" / ") || "default";
}

function csvList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}

function numberField(form: FormData, key: string, fallback: number): number {
  const value = optionalFormString(form, key);
  if (value === null) {
    return fallback;
  }
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function checkbox(form: FormData, key: string): boolean {
  return form.get(key) === "on";
}

function sceneLayers(value: Record<string, unknown>): SceneComposeResult["output_objects"] extends never
  ? never
  : Array<{
      asset_id: string;
      x: number;
      y: number;
      width?: number | null;
      height?: number | null;
      opacity?: number;
      z_index?: number;
      blend_mode?: string | null;
    }> {
  const rawLayers = Array.isArray(value.layers) ? value.layers : [];
  return rawLayers.map((entry) => {
    const layer = entry as Record<string, unknown>;
    return {
      asset_id: String(layer.asset_id ?? ""),
      x: numberValue(layer.x, 0),
      y: numberValue(layer.y, 0),
      width: nullableNumber(layer.width),
      height: nullableNumber(layer.height),
      opacity: numberValue(layer.opacity, 1),
      z_index: numberValue(layer.z_index, 0),
      blend_mode: typeof layer.blend_mode === "string" && layer.blend_mode !== "" ? layer.blend_mode : null,
    };
  });
}

function defaultLayers(assets: MediaAsset[]): { layers: Array<{ asset_id: string; x: number; y: number; z_index: number }> } {
  return {
    layers: assets.slice(0, 2).map((asset, index) => ({
      asset_id: asset.id,
      x: 120 + index * 220,
      y: 120,
      z_index: index + 1,
    })),
  };
}

function numberValue(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }
  return fallback;
}

function nullableNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  return numberValue(value, 0);
}

function restrictedVisibility(value: VisualVisibility): boolean {
  return value === "developer_only" || value === "hidden";
}

function safeJsonSummary(value: Record<string, unknown>): string {
  const keys = Object.keys(value).filter((key) => !sensitiveJsonKey(key));
  if (keys.length === 0) {
    return "{}";
  }
  return keys.slice(0, 6).join(", ");
}

function sensitiveJsonKey(key: string): boolean {
  const normalized = key.toLowerCase();
  return [
    "storage",
    "uri",
    "path",
    "base64",
    "bytes",
    "prompt",
    "output",
    "secret",
    "token",
    "authorization",
  ].some((piece) => normalized.includes(piece));
}

function sanitizeJsonForDisplay(value: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(value)
      .filter(([key]) => !sensitiveJsonKey(key))
      .map(([key, entry]) => [key, sanitizeJsonValue(entry)]),
  );
}

function sanitizeJsonValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((entry) => sanitizeJsonValue(entry));
  }
  if (value !== null && typeof value === "object") {
    return sanitizeJsonForDisplay(value as Record<string, unknown>);
  }
  if (typeof value === "string" && looksSensitiveString(value)) {
    return "[redacted]";
  }
  return value;
}

function looksSensitiveString(value: string): boolean {
  return /media:\/\/|base64|\/var\/|\/tmp\/|[A-Za-z]:\\/.test(value);
}

function shortId(value: string): string {
  return value.length <= 12 ? value : `${value.slice(0, 8)}...${value.slice(-4)}`;
}
