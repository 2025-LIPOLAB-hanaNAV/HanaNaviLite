import imgBackground2 from "figma:asset/f9d07d38f0acec59ac606b39b181a4ae8fbe1cd1.png";
import imgTest1 from "figma:asset/4510f7fccec88b7d96239af9f1cbab26b3e402cd.png";
import { imgLogo, imgIsologo, imgIcon } from "./svg-y0184";

function Wrapper() {
  return (
    <div className="absolute contents left-[-384.53px] top-[-19.13px]" data-name="Wrapper">
      <div className="absolute bg-center bg-cover bg-no-repeat h-[1663px] left-[-384.53px] top-[-19.13px] w-[2001px]" data-name="Background-2" style={{ backgroundImage: `url('${imgBackground2}')` }} />
      <div className="absolute bg-center bg-cover bg-no-repeat h-[1296.57px] left-[40.61px] top-[595.75px] w-[1650.77px]" data-name="test 1" style={{ backgroundImage: `url('${imgTest1}')` }} />
    </div>
  );
}

function Logo() {
  return (
    <div className="[grid-area:1_/_1] h-[53.045px] ml-[18.351%] mt-[15.159%] relative w-[397.536px]" data-name="Logo">
      <img className="block max-w-none size-full" src={imgLogo} />
    </div>
  );
}

function Isologo() {
  return (
    <div className="[grid-area:1_/_1] h-16 ml-0 mt-0 relative w-[64.001px]" data-name="Isologo">
      <img className="block max-w-none size-full" src={imgIsologo} />
    </div>
  );
}

function LogoWrapper() {
  return (
    <div className="grid-cols-[max-content] grid-rows-[max-content] inline-grid leading-[0] place-items-start relative shrink-0" data-name="Logo Wrapper">
      <Logo />
      <Isologo />
    </div>
  );
}

function Logo1() {
  return (
    <div className="content-stretch flex gap-[16.131px] h-16 items-center justify-start relative shrink-0 w-[486.883px]" data-name="Logo">
      <LogoWrapper />
    </div>
  );
}

function Component14Px() {
  return (
    <div className="content-stretch flex flex-col gap-3.5 items-center justify-start leading-[0] not-italic relative shrink-0 text-center" data-name="14px">
      <div className="font-['Inter:Extra_Bold',_sans-serif] font-extrabold relative shrink-0 text-[#0d0a2c] text-[70px] w-[874.333px]">
        <p className="leading-[86px]">Thanks for downloading our Figma cloneable</p>
      </div>
      <div className="font-['Inter:Regular',_sans-serif] font-normal relative shrink-0 text-[#667394] text-[0px] w-[1256.84px]">
        <p className="leading-[52px] text-[30px] whitespace-pre-wrap">
          <span>{`Thanks for downloading our `}</span>
          <span className="font-['Inter:Bold',_sans-serif] font-bold not-italic text-[#0d0a2c]">Chart UI Components</span>
          <span>{`, we hope it is useful for you. If you are looking for more amazing free Figma Templates, we recommend you to follow us in the `}</span>
          <a className="[text-decoration-skip-ink:none] [text-underline-position:from-font] cursor-pointer decoration-solid font-['Inter:Regular',_sans-serif] font-normal not-italic text-[#4a3aff] underline" href="https://www.figma.com/@brixtemplates">
            <span className="[text-decoration-skip-ink:none] [text-underline-position:from-font] decoration-solid leading-[52px]" href="https://www.figma.com/@brixtemplates">
              Figma Community
            </span>
          </a>
          <span>{`, or get one of  our premium website templates from `}</span>
          <a className="[text-decoration-skip-ink:none] [text-underline-position:from-font] cursor-pointer decoration-solid font-['Inter:Regular',_sans-serif] font-normal not-italic text-[#4a3aff] underline" href="https://brixtemplates.com/figma">
            <span className="[text-decoration-skip-ink:none] [text-underline-position:from-font] decoration-solid leading-[52px]" href="https://brixtemplates.com/figma">
              BRIXTemplates.com
            </span>
          </a>
          .
        </p>
      </div>
    </div>
  );
}

function Component28Px() {
  return (
    <div className="content-stretch flex flex-col gap-7 items-center justify-start relative shrink-0" data-name="28px">
      <Logo1 />
      <Component14Px />
    </div>
  );
}

function Icon() {
  return (
    <div className="h-[15.42px] relative shrink-0 w-[16.402px]" data-name="Icon">
      <div className="absolute inset-[-10%_-9.4%]">
        <img className="block max-w-none size-full" src={imgIcon} />
      </div>
    </div>
  );
}

function PrimaryBtn() {
  return (
    <div className="bg-[#4a3aff] box-border content-stretch flex gap-[11.75px] items-start justify-start px-[61.1px] py-[37.6px] relative rounded-[86.35px] shadow-[0px_4.626px_18.504px_0px_rgba(74,58,255,0.28)] shrink-0" data-name="Primary BTN">
      <a className="[white-space-collapse:collapse] flex flex-col font-['Inter:Bold',_sans-serif] font-bold justify-center leading-[0] not-italic relative shrink-0 text-[25.85px] text-center text-nowrap text-white" href="https://brixtemplates.com/figma">
        <p className="cursor-pointer leading-[29.723px] whitespace-pre">Browse templates</p>
      </a>
      <Icon />
    </div>
  );
}

function Component40Px() {
  return (
    <div className="absolute content-stretch flex flex-col gap-10 items-center justify-start left-1/2 top-[94px] translate-x-[-50%]" data-name="40px">
      <Component28Px />
      <PrimaryBtn />
    </div>
  );
}

function BrixTemplates() {
  return (
    <div className="absolute bg-[#f8f9ff] h-[1644px] left-0 overflow-clip rounded-[98px] shadow-[0px_12px_34px_0px_rgba(4,16,34,0.06),0px_84px_250px_0px_rgba(7,33,102,0.12)] top-0 w-[1616px]" data-name="BRIX Templates">
      <Wrapper />
      <Component40Px />
    </div>
  );
}

export default function BrixTemplates1() {
  return (
    <div className="relative size-full" data-name="BRIX Templates">
      <BrixTemplates />
    </div>
  );
}