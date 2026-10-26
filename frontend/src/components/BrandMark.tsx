/** Shared mark for navigation, authentication, loading and error screens. */
export function BrandMark() {
  return <img className="brand-symbol" src={`${import.meta.env.BASE_URL}brand-mark.svg`} width="96" height="96" alt="" aria-hidden="true" />;
}
