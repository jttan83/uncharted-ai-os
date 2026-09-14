import type { Meta, StoryObj } from "@storybook/react";
import "@/i18n";
import { INITIAL_CAPABILITIES_FIXTURE } from "../__fixtures__/initial-capabilities";
import { CapabilitySkillTree } from "./CapabilitySkillTree";

const meta: Meta<typeof CapabilitySkillTree> = {
  title: "Uncharted AI OS/Capability SkillTree",
  component: CapabilitySkillTree,
  decorators: [
    (Story) => (
      <div className="h-screen w-screen bg-background p-6">
        <Story />
      </div>
    ),
  ],
  parameters: { layout: "fullscreen" },
  args: {
    capabilities: INITIAL_CAPABILITIES_FIXTURE,
    scopeKey: "storybook-fixture",
    onCapabilitySelect: () => undefined,
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const InitialCapabilities: Story = {};
